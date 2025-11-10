"""
Gradio Demo Interface for Ethereum Wallet Credit Scoring API

This demo provides an interactive web interface to test both API endpoints:
1. /enquiry - Get credit score and features
2. /report - Get LLM-generated markdown report
"""

import gradio as gr
import httpx
import asyncio
from typing import Tuple
import json

# API configuration
API_BASE_URL = "http://localhost:8000"


async def check_api_health() -> Tuple[bool, str]:
    """Check if the API is running and healthy"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{API_BASE_URL}/health")
            if response.status_code == 200:
                return True, "✅ API is healthy and ready"
            else:
                return False, f"⚠️ API returned status code {response.status_code}"
    except httpx.ConnectError:
        return False, "❌ Cannot connect to API. Please start the server first:\n`uvicorn main:app --reload`"
    except Exception as e:
        return False, f"❌ Error connecting to API: {str(e)}"


async def get_credit_enquiry(wallet_address: str) -> Tuple[str, str, str]:
    """
    Call the /enquiry endpoint and return formatted results
    
    Returns:
        Tuple of (status_message, credit_score_text, features_json)
    """
    try:
        # Validate wallet address format
        if not wallet_address:
            return "⚠️ Please enter a wallet address", "", ""
        
        if not wallet_address.startswith("0x"):
            return "⚠️ Wallet address must start with '0x'", "", ""
        
        if len(wallet_address) != 42:
            return "⚠️ Wallet address must be 42 characters (including 0x prefix)", "", ""
        
        # Show loading message
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f"{API_BASE_URL}/v1/wallet/{wallet_address.lower()}/enquiry"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Format credit score
                credit_score = data.get('credit_score', 0)
                score_text = f"# 🎯 Credit Score: {credit_score:.2f}\n\n"
                
                # Add interpretation based on grade ranges
                if credit_score >= 700:
                    score_text += "**Grade:** 1 | **Rating:** 🟢 Ultra Low Risk (A++)\n"
                    score_text += "This wallet demonstrates exceptional creditworthiness with outstanding on-chain activity and reliability."
                elif credit_score >= 653:
                    score_text += "**Grade:** 2 | **Rating:** 🟢 Very Low Risk (A+)\n"
                    score_text += "This wallet shows very strong creditworthiness with high activity and excellent reliability."
                elif credit_score >= 600:
                    score_text += "**Grade:** 3 | **Rating:** 🟡 Low Risk (A)\n"
                    score_text += "This wallet displays solid creditworthiness with consistent activity and good reliability."
                elif credit_score >= 570:
                    score_text += "**Grade:** 4 | **Rating:** 🟠 Moderate Risk (B)\n"
                    score_text += "This wallet shows moderate creditworthiness with regular activity but some limitations."
                elif credit_score >= 528:
                    score_text += "**Grade:** 5 | **Rating:** 🔴 High Risk (C)\n"
                    score_text += "This wallet has limited creditworthiness with reduced activity or concerning patterns."
                else:
                    score_text += "**Grade:** 6 | **Rating:** 🔴 Very High Risk (C-)\n"
                    score_text += "This wallet shows minimal creditworthiness with very limited activity or significant concerns."
                
                score_text += f"\n**Wallet:** `{data.get('wallet_address', 'N/A')}`"
                score_text += f"\n**Message:** {data.get('message', 'N/A')}"
                
                # Format features as JSON with nice indentation
                features = data.get('features', {})
                
                # Create a summary table for key features
                key_features = {
                    'Account Age (days)': features.get('account_age_days', 0),
                    'Total Transactions': features.get('total_transactions', 0),
                    'Total ETH Sent': f"{features.get('total_eth_sent', 0):.4f}",
                    'Total ETH Received': f"{features.get('total_eth_received', 0):.4f}",
                    'Net ETH Change': f"{features.get('net_eth_change', 0):.4f}",
                    'Unique Counterparties': features.get('unique_counterparties', 0),
                    'Contract Interactions': features.get('contract_interactions', 0),
                    'Failed Transaction Ratio': f"{features.get('failed_tx_ratio', 0):.4f}",
                    'Days Since Last TX': features.get('days_since_last_tx', 0),
                }
                
                summary = "\n\n## 📊 Key Features\n\n"
                for key, value in key_features.items():
                    summary += f"- **{key}:** {value}\n"
                
                score_text += summary
                
                # Full features as formatted JSON
                features_json = json.dumps(features, indent=2)
                
                return "✅ Successfully retrieved credit score", score_text, features_json
            
            elif response.status_code == 404:
                return "❌ Wallet not found or no transaction history", "", ""
            else:
                error_detail = response.json().get('detail', 'Unknown error')
                return f"❌ API Error: {error_detail}", "", ""
    
    except httpx.TimeoutException:
        return "⏱️ Request timed out. The wallet may have a large transaction history. Please try again.", "", ""
    except Exception as e:
        return f"❌ Error: {str(e)}", "", ""


async def get_wallet_report(wallet_address: str) -> Tuple[str, str]:
    """
    Call the /report endpoint and return the markdown report
    
    Returns:
        Tuple of (status_message, markdown_report)
    """
    try:
        # Validate wallet address format
        if not wallet_address:
            return "⚠️ Please enter a wallet address", ""
        
        if not wallet_address.startswith("0x"):
            return "⚠️ Wallet address must start with '0x'", ""
        
        if len(wallet_address) != 42:
            return "⚠️ Wallet address must be 42 characters (including 0x prefix)", ""
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(
                f"{API_BASE_URL}/v1/wallet/{wallet_address.lower()}/report"
            )
            
            if response.status_code == 200:
                report = response.text
                return "✅ Successfully generated AI-powered report", report
            
            elif response.status_code == 404:
                return "❌ Wallet not found or no transaction history", ""
            else:
                try:
                    error_detail = response.json().get('detail', 'Unknown error')
                except Exception:
                    error_detail = response.text
                return f"❌ API Error: {error_detail}", ""
    
    except httpx.TimeoutException:
        return "⏱️ Request timed out. Generating the AI report may take longer for complex wallets. Please try again.", ""
    except Exception as e:
        return f"❌ Error: {str(e)}", ""


# Synchronous wrappers for Gradio
def sync_check_api_health():
    """Synchronous wrapper for health check"""
    healthy, message = asyncio.run(check_api_health())
    return message


def sync_get_credit_enquiry(wallet_address: str):
    """Synchronous wrapper for credit enquiry"""
    return asyncio.run(get_credit_enquiry(wallet_address))


def sync_get_wallet_report(wallet_address: str):
    """Synchronous wrapper for wallet report"""
    return asyncio.run(get_wallet_report(wallet_address))


# Sample wallet addresses for quick testing
SAMPLE_WALLETS = {
    "Vitalik Buterin": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    "Moderate Risk Sample": "0xdadb0d80178819f2319190d340ce9a924f783711",
}


def load_sample_wallet(wallet_name: str) -> str:
    """Load a sample wallet address"""
    return SAMPLE_WALLETS.get(wallet_name, "")


# Create Gradio interface with custom theme and styling
custom_css = """
    * {
        font-family: Arial, sans-serif !important;
    }
    .gradio-container {
        max-width: 1400px !important;
    }
    .header-text {
        text-align: center;
        margin-bottom: 2rem;
    }
    .status-box {
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .score-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        font-size: 1.2rem;
        margin: 1rem 0;
    }
    .feature-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    .footer-text {
        text-align: center;
        color: #666;
        font-size: 0.9rem;
        margin-top: 2rem;
        padding-top: 2rem;
        border-top: 1px solid #ddd;
    }
"""

with gr.Blocks(
    title="Ethereum Wallet Credit Scoring",
    theme=gr.themes.Soft(
        primary_hue="indigo",
        secondary_hue="purple",
        neutral_hue="slate",
    ),
    css=custom_css
) as demo:
    
    # Header with animated gradient
    gr.Markdown(
        """
        # 🔗 Ethereum Wallet Credit Scoring
        
        ### 🚀 Analyze On-Chain Activity & Generate AI-Powered Credit Reports
        
        <div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, #667eea22 0%, #764ba222 100%); border-radius: 12px; margin: 1rem 0;">
        
        **Two Powerful Analysis Methods:**
        
        📊 **Credit Enquiry** - Lightning-fast scoring with 50+ on-chain features  
        📝 **AI Report** - Comprehensive analysis powered by LLM from OpenRouter/Amazon Bedrock
        
        </div>
        
        ---
        """,
        elem_classes=["header-text"]
    )
    
    # API Health Status
    with gr.Row():
        with gr.Column():
            health_status = gr.Textbox(
                label="🏥 API Health Status",
                value="Checking...",
                interactive=False,
                lines=2
            )
            health_check_btn = gr.Button("🔄 Check API Health", size="sm")
    
    health_check_btn.click(
        fn=sync_check_api_health,
        outputs=health_status
    )
    
    # Load initial health status
    demo.load(fn=sync_check_api_health, outputs=health_status)
    
    gr.Markdown("---")
    
    # Main Interface
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 🔍 Enter Wallet Address")
            
            wallet_input = gr.Textbox(
                label="Ethereum Wallet Address",
                placeholder="0x...",
                info="Enter a valid Ethereum wallet address (42 characters)",
                lines=1
            )
            
            # Sample wallets dropdown
            gr.Markdown("**Or try a sample wallet:**")
            sample_dropdown = gr.Dropdown(
                choices=list(SAMPLE_WALLETS.keys()),
                label="Sample Wallets",
                info="Select a well-known wallet to test"
            )
            
            sample_dropdown.change(
                fn=load_sample_wallet,
                inputs=sample_dropdown,
                outputs=wallet_input
            )
            
            gr.Markdown("---")
            
            with gr.Row():
                enquiry_btn = gr.Button("📊 Get Credit Score", variant="primary", size="lg")
                report_btn = gr.Button("📝 Generate AI Report", variant="secondary", size="lg")
    
    # Tab interface for results
    with gr.Column(scale=2):
        with gr.Tabs():
            # Credit Enquiry Tab
            with gr.Tab("📊 Credit Score & Features"):
                enquiry_status = gr.Textbox(
                    label="Status",
                    interactive=False,
                    lines=1
                )
                
                with gr.Row():
                    with gr.Column():
                        credit_score_output = gr.Markdown(
                            label="Credit Score Analysis",
                            value="Enter a wallet address and click 'Get Credit Score' to see results."
                        )
                    
                    with gr.Column():
                        features_output = gr.Code(
                            label="All Extracted Features (JSON)",
                            language="json",
                            lines=20
                        )
            
            # AI Report Tab
            with gr.Tab("📝 AI-Powered Report"):
                report_status = gr.Textbox(
                    label="Status",
                    interactive=False,
                    lines=1
                )
                
                report_output = gr.Markdown(
                    label="Wallet Credit Report",
                    value="Enter a wallet address and click 'Generate AI Report' to see results.\n\n*Note: Report generation may take 30-60 seconds depending on LLM response time.*"
                )
    
    # Button click handlers
    enquiry_btn.click(
        fn=sync_get_credit_enquiry,
        inputs=wallet_input,
        outputs=[enquiry_status, credit_score_output, features_output]
    )
    
    report_btn.click(
        fn=sync_get_wallet_report,
        inputs=wallet_input,
        outputs=[report_status, report_output]
    )


if __name__ == "__main__":
    print("🚀 Starting Gradio Demo Interface...")
    print(f"📡 API Base URL: {API_BASE_URL}")
    print("\n⚠️  Make sure your FastAPI server is running:")
    print("   uvicorn main:app --reload")
    print("\n🌐 Gradio interface will be available at the URL shown below:\n")
    
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
