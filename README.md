# Ethereum Wallet Credit Scoring

## Overview

FastAPI service for credit scoring Ethereum wallets using on-chain transaction analysis and AI-powered reporting.

## Features

- 🎯 Credit scoring based on on-chain activity
- 📊 50+ feature extraction from transaction history
- 🤖 AI-generated reports using LLMs (Claude/GPT)
- 🎨 Interactive Gradio web interface
- 📈 Scorecard-based risk grading (Grade 1-6)

## Quick Start

1. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

2. **Configure API keys:**
   - Copy `.env.example` to `.env`
   - Add your `ETHERSCAN_API_KEY` from [Etherscan](https://etherscan.io/myapikey)
   - Add your `OPENROUTER_API_KEY` from [OpenRouter](https://openrouter.ai/keys)

3. **Launch the application:**
   ```powershell
   .\start_all.ps1
   ```

4. **Access the interface:**
   - Gradio Demo: `http://localhost:7860`
   - API Server: `http://localhost:8000`
   - API Docs: `http://localhost:8000/docs`

## Credit Score Grading

| Grade | Score Range | Risk Category | Rating |
|-------|-------------|---------------|--------|
| 1 | 700+ | Ultra Low Risk | A++ 🟢 |
| 2 | 653-699 | Very Low Risk | A+ 🟢 |
| 3 | 600-652 | Low Risk | A 🟡 |
| 4 | 570-599 | Moderate Risk | B 🟠 |
| 5 | 528-569 | High Risk | C 🔴 |
| 6 | <528 | Very High Risk | C- 🔴 |

## API Endpoints

- `GET /v1/wallet/{address}/enquiry` - Get credit score and features
- `GET /v1/wallet/{address}/report` - Generate AI report
- `GET /health` - Health check

## Project Structure

```
credit_scoring_onchain/
├── main.py                    # FastAPI server
├── gradio_demo.py            # Web interface
├── requirements.txt          # Dependencies
├── start_all.ps1            # Launch script
├── .env                     # Configuration (create from .env.example)
├── prompts/
│   └── wallet_report.prompty
└── services/
    ├── credit_scoring_service.py
    └── etherscan_service.py
```
