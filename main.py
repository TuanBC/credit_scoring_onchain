"""
FastAPI application for Ethereum wallet credit scoring.

This API provides an endpoint to calculate credit scores for Ethereum wallets
by fetching transaction history from Etherscan and extracting features.
"""

from fastapi import FastAPI, HTTPException, Path
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import os
import logging
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_aws import ChatBedrockConverse
from jinja2 import Environment, FileSystemLoader

from services.etherscan_service import EtherscanService
from services.credit_scoring_service import CreditScoringService
from services.offchain_data_generator import OffchainDataGenerator
import numpy as np
def convert_numpy(obj):
    """Recursively convert numpy types to native Python types."""
    if isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy(v) for v in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, (np.bool_, np.bool)):
        return bool(obj)
    else:
        return obj

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Ethereum Wallet Credit Scoring API",
    description="API for calculating credit scores for Ethereum wallets based on transaction history",
    version="1.0.0"
)

# Initialize services
etherscan_api_key = os.getenv("ETHERSCAN_API_KEY")
if not etherscan_api_key:
    raise ValueError("ETHERSCAN_API_KEY environment variable is required")

openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
if not openrouter_api_key:
    raise ValueError("OPENROUTER_API_KEY environment variable is required")

# Get model from environment, default to Claude 3.5 Sonnet
openrouter_model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")

etherscan_service = EtherscanService(api_key=etherscan_api_key)
credit_scoring_service = CreditScoringService()
offchain_generator = OffchainDataGenerator()


# Select LLM provider: 'openrouter' or 'bedrock'
llm_provider = os.getenv("LLM_PROVIDER", "openrouter").lower()
llm = None
if llm_provider == "bedrock":
    bedrock_model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")
    bedrock_region = os.getenv("BEDROCK_REGION", "us-west-2")
    # AWS credentials are read from env vars or IAM role
    llm = ChatBedrockConverse(
        model_id=bedrock_model_id,
        region_name=bedrock_region,
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),  # Optional
        temperature=0.7,
        max_tokens=2000,
    )
elif llm_provider == "openrouter":
    llm = ChatOpenAI(
        model=openrouter_model,
        api_key=openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0.7,
        max_tokens=2000,
    )
else:
    raise ValueError(f"Unsupported LLM_PROVIDER: {llm_provider}")

# Initialize Jinja2 environment for Prompty templates
prompts_dir = os.path.join(os.path.dirname(__file__), "prompts")
jinja_env = Environment(loader=FileSystemLoader(prompts_dir))

def load_prompty_template(template_name: str) -> str:
    """Load and parse a .prompty file, extracting the template content"""
    template_path = os.path.join(prompts_dir, template_name)
    with open(template_path, 'r') as f:
        content = f.read()
    # Split on --- to separate metadata from template
    parts = content.split('---\n', 2)
    if len(parts) >= 3:
        # Return the template part (after the second ---)
        return parts[2].strip()
    return content.strip()

def render_prompty_template(template_name: str, data: Dict[str, Any]) -> str:
    """Load a .prompty template and render it with the given data"""
    template_content = load_prompty_template(template_name)
    template = jinja_env.from_string(template_content)
    return template.render(**data)


class CreditScoreResponse(BaseModel):
    """Response model for credit score enquiry"""
    wallet_address: str
    credit_score: float
    features: Dict[str, Any]
    message: Optional[str] = None


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Ethereum Wallet Credit Scoring API",
        "version": "1.0.0",
        "endpoints": {
            "enquiry": "/v1/wallet/{wallet_address}/enquiry",
            "report": "/v1/wallet/{wallet_address}/report"
        }
    }


@app.get("/v1/wallet/{wallet_address}/enquiry", response_model=CreditScoreResponse)
async def enquire_wallet_credit_score(
    wallet_address: str = Path(..., description="Ethereum wallet address", min_length=42, max_length=42)
) -> CreditScoreResponse:
    """
    Get credit score for an Ethereum wallet.
    
    This endpoint:
    1. Fetches transaction history from Etherscan API
    2. Extracts credit features from the transaction data
    3. Optionally fetches additional card info from Etherscan
    4. Calculates and returns the final credit score
    
    Args:
        wallet_address: Ethereum wallet address (42 characters including 0x prefix)
    
    Returns:
        CreditScoreResponse containing the credit score and extracted features
    """
    try:
        # Validate wallet address format
        if not wallet_address.startswith("0x"):
            raise HTTPException(status_code=400, detail="Wallet address must start with '0x'")
        
        wallet_address = wallet_address.lower()
        
        # Step 1: Fetch transaction history from Etherscan
        transactions = await etherscan_service.fetch_transactions(wallet_address)
        
        if not transactions:
            return CreditScoreResponse(
                wallet_address=wallet_address,
                credit_score=0.0,
                features={},
                message="No transaction history found for this wallet"
            )
        
        # Step 2: Extract credit features from transactions
        features = credit_scoring_service.extract_features(transactions, wallet_address)
        
        # Step 3: Calculate credit score using scorecard
        credit_score = credit_scoring_service.calculate_scorecard_credit_score(features)
        
        # Convert numpy types in features
        features = convert_numpy(features)
        credit_score = float(credit_score)  # Ensure float

        # Step 4: Generate off-chain persona data
        offchain_data = offchain_generator.generate(wallet_address, features)
        logger.info(f"Generated off-chain data for wallet: {wallet_address}")
        for key, value in offchain_data.items():
            logger.info(f"  {key}: {value}")
        
        # Combine on-chain and off-chain features
        complete_features = {**features, **offchain_data}

        return CreditScoreResponse(
            wallet_address=wallet_address,
            credit_score=credit_score,
            features=complete_features,
            message="Credit score calculated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing wallet credit score: {str(e)}"
        )


@app.get("/v1/wallet/{wallet_address}/report", response_class=PlainTextResponse)
async def generate_wallet_report(
    wallet_address: str = Path(..., description="Ethereum wallet address", min_length=42, max_length=42)
) -> str:
    """
    Generate an LLM-powered markdown report for an Ethereum wallet.
    
    This endpoint performs the same analysis as /enquiry but returns a comprehensive
    markdown report generated by an LLM via OpenRouter.
    
    Args:
        wallet_address: Ethereum wallet address (42 characters including 0x prefix)
    
    Returns:
        Markdown-formatted report analyzing the wallet's credit profile
    """
    try:
        # Validate wallet address format
        if not wallet_address.startswith("0x"):
            raise HTTPException(status_code=400, detail="Wallet address must start with '0x'")
        
        wallet_address = wallet_address.lower()
        
        # Step 1: Fetch transaction history from Etherscan
        transactions = await etherscan_service.fetch_transactions(wallet_address)
        
        if not transactions:
            return f"# Wallet Credit Report\n\n**Wallet Address:** `{wallet_address}`\n\n## Summary\n\nNo transaction history found for this wallet. Unable to generate credit assessment."
        
        # Step 2: Extract credit features from transactions
        features = credit_scoring_service.extract_features(transactions, wallet_address)
        
        # Step 3: Calculate credit score using scorecard
        credit_score = credit_scoring_service.calculate_scorecard_credit_score(features)
        
        # Convert numpy types
        features = convert_numpy(features)
        credit_score = float(credit_score)
        
        # Step 4: Generate off-chain persona data
        offchain_data = offchain_generator.generate(wallet_address, features)
        logger.info(f"Generated off-chain data for wallet: {wallet_address}")
        for key, value in offchain_data.items():
            logger.info(f"  {key}: {value}")
        
        # Step 5: Prepare data for LLM
        # Combine on-chain and off-chain features
        complete_features = {**features, **offchain_data}
        
        # Prepare a preview of the first 20 features for the template
        features_preview = list(complete_features.items())[:20]
        report_data = {
            "wallet_address": wallet_address,
            "credit_score": credit_score,
            "transaction_count": len(transactions),
            "features": complete_features,
            "features_preview": features_preview,
            "offchain_data": offchain_data
        }


        # Step 6: Render prompt using Prompty template with Jinja2
        prompt = render_prompty_template("wallet_report.prompty", report_data)

        # Use LangChain's async ainvoke for FastAPI (provider-agnostic)
        messages = [{"role": "user", "content": prompt}]
        response = await llm.ainvoke(messages)
        report = response.text
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating wallet report: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "credit-scoring-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
