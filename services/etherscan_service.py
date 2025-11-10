"""
Etherscan API service for fetching wallet transaction data.
"""

from typing import List, Dict, Any
import aiohttp
from bs4 import BeautifulSoup


class EtherscanService:
    """Service for interacting with Etherscan API"""
    
    ETHERSCAN_API_BASE = "https://api.etherscan.io/v2/api"
    ETHERSCAN_CARDS_URL = "https://etherscan.io/address-cards.aspx/GetMoreCards"
    
    def __init__(self, api_key: str):
        """
        Initialize Etherscan service.
        
        Args:
            api_key: Etherscan API key
        """
        self.api_key = api_key
    
    async def fetch_transactions(
        self, 
        address: str, 
        startblock: int = 0, 
        endblock: int = 99999999,
        sort: str = "asc"
    ) -> List[Dict[str, Any]]:
        """
        Fetch transaction list from Etherscan with pagination.
        
        Args:
            address: Ethereum wallet address
            startblock: Starting block number
            endblock: Ending block number
            sort: Sort order ('asc' or 'desc')
        
        Returns:
            List of transaction dictionaries
        """
        async with aiohttp.ClientSession() as session:
            # Simple format matching the reference implementation
            params = {
                "module": "account",
                "action": "txlist",
                "chainid": "1",
                "address": address,
                "sort": sort,
                "apikey": self.api_key,
            }
            
            async with session.get(self.ETHERSCAN_API_BASE, params=params, timeout=30) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Etherscan HTTP {resp.status}: {text}")
                
                data = await resp.json()
                
                status = data.get("status")
                message = data.get("message", "")
                
                # Handle empty results
                if status == "0" and isinstance(data.get("result"), list) and len(data.get("result", [])) == 0:
                    return []
                
                # Handle error messages
                if status == "0" and data.get("result") is None:
                    # If it's just "No transactions found", return empty list
                    if "No transactions found" in message or "No records found" in message:
                        return []
                    raise RuntimeError(f"Etherscan API error: {message}")
                
                # Get results
                results = data.get("result", [])
                if not isinstance(results, list):
                    raise RuntimeError(f"Unexpected Etherscan response format: {data}")
                
                return results
    
    async def fetch_card_info(self, address: str) -> Dict[str, Any]:
        """
        Fetch additional card information from Etherscan.
        
        This scrapes the Etherscan address cards page to get additional
        information like credit scores, reputation, attestations, etc.
        
        Args:
            address: Ethereum wallet address
        
        Returns:
            Dictionary with card information
        """
        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json',
            'origin': 'https://etherscan.io',
            'referer': f'https://etherscan.io/address-cards?m=light&a={address}&t=EOA,%20EOAHighActivity',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }
        
        json_data = {
            'getMoreCardsRequest': {
                'address': address,
                'addressType': 'EOA, EOAHighActivity',
                'page': 1,
                'favouriteOnly': False,
            },
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.ETHERSCAN_CARDS_URL, headers=headers, json=json_data, timeout=30) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Etherscan cards HTTP {resp.status}: {text}")
                
                response_json = await resp.json()
                html = response_json.get('d', {}).get('Result', {}).get('result', '')
                
                if not html:
                    return {}
                
                return self._parse_cards_html(html)
    
    def _parse_cards_html(self, html: str) -> Dict[str, Any]:
        """
        Parse the HTML from Etherscan cards response.
        
        Args:
            html: HTML content from Etherscan
        
        Returns:
            Dictionary with parsed card information
        """
        import re
        
        soup = BeautifulSoup(html, 'html.parser')
        result = {}
        
        for card_div in soup.find_all('div', class_='address-card'):
            # Title
            title_tag = card_div.find('h3', class_='card-header-title')
            if not title_tag:
                continue
            
            title_text = title_tag.get_text(strip=True)
            title_text = re.sub(r'\d+$', '', title_text).strip()
            
            # Main value
            value = None
            value_tag = card_div.find('div', id='gaugeValue')
            if value_tag:
                value = value_tag.get_text(strip=True)
            else:
                h4_tag = card_div.find('h4', class_='fs-5 mb-3')
                if h4_tag:
                    strong_tag = h4_tag.find('strong')
                    if strong_tag:
                        value = strong_tag.get_text(strip=True)
                else:
                    h4s = card_div.find_all('h4')
                    for h4 in h4s:
                        h4_text = h4.get_text(strip=True).lower()
                        match = re.search(r'(\d+)', h4_text)
                        if match:
                            value = match.group(1)
                            break
                        if ('no badges' in h4_text or 'no attestations' in h4_text or 
                            'no poaps' in h4_text or re.search(r'0/\d+', h4_text)):
                            value = '0'
                            break
            
            # Convert to snake_case key
            key = self._to_snake_case(title_text)
            result[key] = self._to_numeric(value) if value else 0
        
        return result
    
    @staticmethod
    def _to_snake_case(s: str) -> str:
        """Convert string to snake_case"""
        import re
        replacements = {
            'IDM': 'idm', 'EAS': 'eas', 'POAP': 'poap', 'DAO': 'dao',
            'Credit Score': 'credit_score', 'Builder Score': 'builder_score',
            'AML Risk Score': 'aml_risk_score', 'Reputation Score': 'zscore_reputation_score',
            'Yield Opportunity': 'yield_opportunity'
        }
        for old, new in replacements.items():
            s = s.replace(old, new)
        s = s.strip()
        s = re.sub(r'[^a-zA-Z0-9_ ]', '', s)
        s = s.replace(' ', '_')
        return 'card_' + s.lower()
    
    @staticmethod
    def _to_numeric(val: Any) -> float:
        """Convert value to numeric"""
        try:
            if isinstance(val, str) and val.endswith('%'):
                val = val[:-1]
            if isinstance(val, str) and '.' in val:
                return float(val)
            return int(float(val))
        except (ValueError, TypeError):
            return 0
