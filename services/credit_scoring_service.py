"""
Credit scoring service for calculating credit scores from wallet features.
"""

import pandas as pd
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import math


class CreditScoringService:
    """Service for extracting features and calculating credit scores"""
    
    def extract_features(
        self, 
        transactions: List[Dict[str, Any]], 
        wallet_address: str
    ) -> Dict[str, Any]:
        """
        Extract credit features from transaction history.
        
        Args:
            transactions: List of transaction dictionaries from Etherscan
            wallet_address: Wallet address (lowercase)
        
        Returns:
            Dictionary of extracted features
        """
        # Convert to DataFrame
        df = pd.DataFrame(transactions)
        
        if df.empty:
            return {}
        
        # Check required fields
        required_fields = ['timeStamp', 'value', 'from', 'to']
        missing_fields = [f for f in required_fields if f not in df.columns]
        if missing_fields:
            raise ValueError(f"Missing required fields in transaction data: {missing_fields}")
        
        # Convert data types
        df['timeStamp'] = pd.to_numeric(df['timeStamp'], errors='coerce')
        df['timeStamp'] = pd.to_datetime(df['timeStamp'], unit='s')
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        
        # isError might not be present in all responses
        if 'isError' not in df.columns:
            df['isError'] = 0
        else:
            df['isError'] = pd.to_numeric(df['isError'], errors='coerce')
        
        # Ensure address columns are lowercase strings
        df['from'] = df['from'].astype(str).str.lower()
        df['to'] = df['to'].astype(str).str.lower()
        
        features = {}
        
        # Basic features
        features['account_age_days'] = (df['timeStamp'].max() - df['timeStamp'].min()).days
        features['total_transactions'] = len(df)
        features['avg_tx_per_month'] = len(df) / max(1, ((df['timeStamp'].max() - df['timeStamp'].min()).days / 30))
        
        def wei_to_eth(x):
            return x / 1e18 if x is not None else 0
        
        # ETH flow features
        features['total_eth_sent'] = wei_to_eth(df[df['from'] == wallet_address]['value'].sum())
        features['total_eth_received'] = wei_to_eth(df[df['to'] == wallet_address]['value'].sum())
        features['net_eth_change'] = features['total_eth_received'] - features['total_eth_sent']
        
        # Transaction value features
        features['largest_tx_value'] = wei_to_eth(df['value'].max())
        features['avg_tx_value'] = wei_to_eth(df['value'].mean())
        features['median_tx_value'] = wei_to_eth(df['value'].median())
        
        # Counterparty features
        counterparties = set(df[df['from'] == wallet_address]['to'].dropna().unique())
        counterparties |= set(df[df['to'] == wallet_address]['from'].dropna().unique())
        features['unique_counterparties'] = len(counterparties)
        
        # Contract interactions
        features['contract_interactions'] = df['input'].apply(
            lambda x: isinstance(x, str) and len(str(x)) > 2
        ).sum()
        features['contract_deployments'] = df['contractAddress'].apply(
            lambda x: isinstance(x, str) and len(str(x)) > 2
        ).sum() if 'contractAddress' in df.columns else 0
        
        # Error features
        features['failed_transactions'] = (df['isError'] == 1).sum()
        features['failed_tx_ratio'] = features['failed_transactions'] / max(1, features['total_transactions'])
        
        # Activity features
        features['active_days'] = df['timeStamp'].dt.date.nunique()
        features['days_since_last_tx'] = (
            datetime.now(timezone.utc) - df['timeStamp'].max().replace(tzinfo=timezone.utc)
        ).days
        
        # Transaction patterns
        tx_per_day = df['timeStamp'].dt.date.value_counts()
        features['max_tx_in_a_day'] = tx_per_day.max() if not tx_per_day.empty else 0
        
        # Inactivity
        if len(df) > 1:
            sorted_dates = df['timeStamp'].sort_values()
            inactivity_periods = sorted_dates.diff().dt.days.dropna()
            features['max_inactivity_days'] = inactivity_periods.max() if not inactivity_periods.empty else 0
        else:
            features['max_inactivity_days'] = 0
        
        # Weekday pattern
        features['most_active_weekday'] = int(df['timeStamp'].dt.dayofweek.mode()[0]) if not df.empty else None
        
        # Counterparty diversity (entropy)
        all_counterparties = list(counterparties)
        cp_counts = [
            ((df['to'] == cp) | (df['from'] == cp)).sum() 
            for cp in all_counterparties
        ]
        total_cp = sum(cp_counts)
        entropy = -sum(
            (c/total_cp) * math.log2(c/total_cp) for c in cp_counts if c > 0
        ) if total_cp > 0 else 0
        features['counterparty_entropy'] = entropy
        
        # Largest transactions
        incoming_txs = df[df['to'] == wallet_address]
        outgoing_txs = df[df['from'] == wallet_address]
        features['largest_incoming_tx'] = wei_to_eth(incoming_txs['value'].max()) if not incoming_txs.empty else 0
        features['largest_outgoing_tx'] = wei_to_eth(outgoing_txs['value'].max()) if not outgoing_txs.empty else 0
        
        # Timing features
        if len(df) > 1:
            sorted_dates = df['timeStamp'].sort_values()
            time_diffs = sorted_dates.diff().dt.total_seconds().dropna()
            features['avg_time_between_tx_days'] = time_diffs.mean() / 86400 if not time_diffs.empty else 0
            features['std_time_between_tx_days'] = time_diffs.std() / 86400 if not time_diffs.empty else 0
            features['shortest_time_between_tx_seconds'] = time_diffs.min() if not time_diffs.empty else 0
            features['automated_activity'] = (
                time_diffs.min() is not None and time_diffs.min() < 10
            )
        else:
            features['avg_time_between_tx_days'] = 0
            features['std_time_between_tx_days'] = 0
            features['shortest_time_between_tx_seconds'] = 0
            features['automated_activity'] = False
        
        # Ratio features
        incoming_count = df[df['to'] == wallet_address].shape[0]
        outgoing_count = df[df['from'] == wallet_address].shape[0]
        features['in_out_tx_count_ratio'] = incoming_count / max(1, outgoing_count)
        features['zero_value_tx_ratio'] = (df['value'] == 0).sum() / max(1, len(df))
        features['unique_counterparty_tx_ratio'] = features['unique_counterparties'] / max(1, len(df))
        
        # Repeat counterparty rate
        cp_all = pd.concat([
            df[df['from'] == wallet_address]['to'].dropna(),
            df[df['to'] == wallet_address]['from'].dropna()
        ])
        repeat_cp = cp_all.value_counts()[cp_all.value_counts() > 1].sum() if not cp_all.empty else 0
        features['repeat_counterparty_rate'] = repeat_cp / max(1, len(cp_all))
        
        # Contract ratios
        features['contract_interaction_ratio'] = features['contract_interactions'] / max(1, len(df))
        features['contract_deployments_to_interactions'] = (
            features['contract_deployments'] / max(1, features['contract_interactions'])
        )
        
        # Statistical features
        df_eth_value = df['value'] / 1e18
        features['tx_value_skewness'] = df_eth_value.skew() if len(df) > 1 else 0
        features['tx_value_kurtosis'] = df_eth_value.kurtosis() if len(df) > 1 else 0
        median_val = features['median_tx_value']
        features['tx_above_median_ratio'] = (df_eth_value > median_val).sum() / max(1, len(df))
        
        # Temporal features
        features['first_tx_weekday'] = int(df['timeStamp'].min().dayofweek) if not df.empty else None
        features['last_tx_weekday'] = int(df['timeStamp'].max().dayofweek) if not df.empty else None
        features['months_with_tx'] = df['timeStamp'].dt.to_period('M').nunique()
        
        # Failed transaction streak
        is_failed = df['isError'] == 1
        max_failed_streak = 0
        current_streak = 0
        for v in is_failed:
            if v:
                current_streak += 1
                max_failed_streak = max(max_failed_streak, current_streak)
            else:
                current_streak = 0
        features['max_failed_tx_streak'] = max_failed_streak
        
        # Gas price features
        if 'gasPrice' in df.columns:
            df['gasPrice'] = pd.to_numeric(df['gasPrice'], errors='coerce')
            max_gas_price = df['gasPrice'].max()
            features['max_gas_price_tx_ratio'] = (
                (df['gasPrice'] == max_gas_price).sum() / max(1, len(df))
            )
        else:
            features['max_gas_price_tx_ratio'] = 0
        
        # Historical features for recent 6 and 12 months
        now = pd.Timestamp.now()
        months_ago_6 = now - pd.DateOffset(months=6)
        months_ago_12 = now - pd.DateOffset(months=12)
        
        for label, cutoff in [('6m', months_ago_6), ('12m', months_ago_12)]:
            dfx = df[df['timeStamp'] >= cutoff]
            features[f'tx_count_{label}'] = int(len(dfx))
            
            dfx_sent = dfx[dfx['from'] == wallet_address]
            features[f'total_eth_sent_{label}'] = float(
                wei_to_eth(dfx_sent['value'].sum())
            ) if not dfx_sent.empty else 0.0
            
            dfx_recv = dfx[dfx['to'] == wallet_address]
            features[f'total_eth_received_{label}'] = float(
                wei_to_eth(dfx_recv['value'].sum())
            ) if not dfx_recv.empty else 0.0
            
            features[f'net_eth_change_{label}'] = (
                features[f'total_eth_received_{label}'] - features[f'total_eth_sent_{label}']
            )
            
            features[f'largest_tx_value_{label}'] = float(
                wei_to_eth(dfx['value'].max())
            ) if not dfx.empty and dfx['value'].notna().any() else 0.0
            
            features[f'avg_tx_value_{label}'] = float(
                wei_to_eth(dfx['value'].mean())
            ) if not dfx.empty and dfx['value'].notna().any() else 0.0
            
            features[f'failed_tx_count_{label}'] = int(
                (dfx['isError'] == 1).sum()
            ) if not dfx.empty else 0
            
            cp = set(dfx[dfx['from'] == wallet_address]['to'].dropna().unique())
            cp |= set(dfx[dfx['to'] == wallet_address]['from'].dropna().unique())
            features[f'unique_counterparties_{label}'] = int(len(cp))
        
        return features
    
    def extract_time_series_data(
        self,
        transactions: List[Dict[str, Any]],
        wallet_address: str
    ) -> Dict[str, Any]:
        """
        Extract time-series data for visualization charts.
        
        Args:
            transactions: List of transaction dictionaries from Etherscan
            wallet_address: Wallet address (lowercase)
        
        Returns:
            Dictionary containing monthly and weekly aggregated data
        """
        df = pd.DataFrame(transactions)
        
        if df.empty:
            return {
                "monthly": [],
                "weekly": [],
                "daily_activity": [],
                "hourly_distribution": [],
                "weekday_distribution": []
            }
        
        # Convert data types
        df['timeStamp'] = pd.to_numeric(df['timeStamp'], errors='coerce')
        df['timeStamp'] = pd.to_datetime(df['timeStamp'], unit='s')
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df['from'] = df['from'].astype(str).str.lower()
        df['to'] = df['to'].astype(str).str.lower()
        
        if 'isError' not in df.columns:
            df['isError'] = 0
        else:
            df['isError'] = pd.to_numeric(df['isError'], errors='coerce')
        
        def wei_to_eth(x):
            return float(x / 1e18) if x is not None else 0.0
        
        time_series = {}
        
        # Monthly aggregations (last 24 months)
        df['month'] = df['timeStamp'].dt.to_period('M')
        monthly_data = []
        
        # Get unique months sorted
        unique_months = sorted(df['month'].unique())
        
        for month in unique_months:
            month_df = df[df['month'] == month]
            month_str = str(month)
            
            sent_df = month_df[month_df['from'] == wallet_address]
            recv_df = month_df[month_df['to'] == wallet_address]
            
            monthly_data.append({
                "month": month_str,
                "tx_count": int(len(month_df)),
                "tx_sent": int(len(sent_df)),
                "tx_received": int(len(recv_df)),
                "eth_sent": wei_to_eth(sent_df['value'].sum()),
                "eth_received": wei_to_eth(recv_df['value'].sum()),
                "net_eth": wei_to_eth(recv_df['value'].sum()) - wei_to_eth(sent_df['value'].sum()),
                "unique_counterparties": int(len(
                    set(sent_df['to'].dropna().unique()) | 
                    set(recv_df['from'].dropna().unique())
                )),
                "avg_tx_value": wei_to_eth(month_df['value'].mean()) if not month_df.empty else 0,
                "failed_tx": int((month_df['isError'] == 1).sum())
            })
        
        time_series['monthly'] = monthly_data[-24:]  # Last 24 months
        
        # Weekly aggregations (last 52 weeks)
        df['week'] = df['timeStamp'].dt.to_period('W')
        weekly_data = []
        
        unique_weeks = sorted(df['week'].unique())
        
        for week in unique_weeks:
            week_df = df[df['week'] == week]
            week_str = str(week)
            
            sent_df = week_df[week_df['from'] == wallet_address]
            recv_df = week_df[week_df['to'] == wallet_address]
            
            weekly_data.append({
                "week": week_str,
                "tx_count": int(len(week_df)),
                "eth_volume": wei_to_eth(week_df['value'].sum()),
                "unique_counterparties": int(len(
                    set(sent_df['to'].dropna().unique()) | 
                    set(recv_df['from'].dropna().unique())
                ))
            })
        
        time_series['weekly'] = weekly_data[-52:]  # Last 52 weeks
        
        # Daily activity heatmap data (last 365 days)
        now = pd.Timestamp.now()
        one_year_ago = now - pd.DateOffset(days=365)
        recent_df = df[df['timeStamp'] >= one_year_ago].copy()
        
        if not recent_df.empty:
            recent_df['date'] = recent_df['timeStamp'].dt.date
            daily_counts = recent_df.groupby('date').size().to_dict()
            
            daily_activity = [
                {"date": str(date), "count": int(count)}
                for date, count in sorted(daily_counts.items())
            ]
        else:
            daily_activity = []
        
        time_series['daily_activity'] = daily_activity
        
        # Hourly distribution (all-time)
        hourly_dist = df['timeStamp'].dt.hour.value_counts().sort_index()
        time_series['hourly_distribution'] = [
            {"hour": int(hour), "count": int(count)}
            for hour, count in hourly_dist.items()
        ]
        
        # Weekday distribution (all-time)
        weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        weekday_dist = df['timeStamp'].dt.dayofweek.value_counts().sort_index()
        time_series['weekday_distribution'] = [
            {"day": weekday_names[day], "day_num": int(day), "count": int(count)}
            for day, count in weekday_dist.items()
        ]
        
        # Transaction value distribution (buckets)
        eth_values = df['value'] / 1e18
        buckets = [0, 0.001, 0.01, 0.1, 1, 10, 100, float('inf')]
        bucket_labels = ['<0.001', '0.001-0.01', '0.01-0.1', '0.1-1', '1-10', '10-100', '>100']
        
        value_distribution = []
        for i in range(len(buckets) - 1):
            count = int(((eth_values >= buckets[i]) & (eth_values < buckets[i+1])).sum())
            value_distribution.append({
                "bucket": bucket_labels[i],
                "count": count
            })
        
        time_series['value_distribution'] = value_distribution
        
        # Cumulative metrics over time
        df_sorted = df.sort_values('timeStamp')
        cumulative_data = []
        
        running_tx = 0
        running_eth_in = 0
        running_eth_out = 0
        
        for month in unique_months:
            month_df = df_sorted[df_sorted['month'] == month]
            running_tx += len(month_df)
            
            sent_df = month_df[month_df['from'] == wallet_address]
            recv_df = month_df[month_df['to'] == wallet_address]
            
            running_eth_in += wei_to_eth(recv_df['value'].sum())
            running_eth_out += wei_to_eth(sent_df['value'].sum())
            
            cumulative_data.append({
                "month": str(month),
                "cumulative_tx": running_tx,
                "cumulative_eth_in": running_eth_in,
                "cumulative_eth_out": running_eth_out,
                "cumulative_net": running_eth_in - running_eth_out
            })
        
        time_series['cumulative'] = cumulative_data
        
        return time_series
    
    def calculate_credit_score(
        self, 
        features: Dict[str, Any], 
        card_info: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate credit score from extracted features.
        
        This is a simplified scoring algorithm. In production, you would use
        a trained machine learning model or a more sophisticated rule-based system.
        
        Args:
            features: Dictionary of extracted features
            card_info: Optional card information from Etherscan
        
        Returns:
            Credit score (0-1000)
        """
        if not features:
            return 0.0
        
        score = 0.0
        
        # Account age component (max 200 points)
        account_age_days = features.get('account_age_days', 0)
        score += min(200, account_age_days / 10)
        
        # Transaction activity component (max 200 points)
        total_transactions = features.get('total_transactions', 0)
        score += min(200, total_transactions / 5)
        
        # ETH volume component (max 200 points)
        total_eth_sent = features.get('total_eth_sent', 0)
        total_eth_received = features.get('total_eth_received', 0)
        total_volume = total_eth_sent + total_eth_received
        score += min(200, math.log1p(total_volume) * 20)
        
        # Counterparty diversity component (max 150 points)
        unique_counterparties = features.get('unique_counterparties', 0)
        counterparty_entropy = features.get('counterparty_entropy', 0)
        score += min(150, unique_counterparties * 2 + counterparty_entropy * 10)
        
        # Contract interaction component (max 100 points)
        contract_interactions = features.get('contract_interactions', 0)
        score += min(100, contract_interactions / 2)
        
        # Recent activity bonus (max 50 points)
        days_since_last_tx = features.get('days_since_last_tx', 365)
        if days_since_last_tx < 30:
            score += 50
        elif days_since_last_tx < 90:
            score += 30
        elif days_since_last_tx < 180:
            score += 10
        
        # Penalize failed transactions (max -100 points)
        failed_tx_ratio = features.get('failed_tx_ratio', 0)
        score -= failed_tx_ratio * 200
        
        # Bonus for consistent activity (max 100 points)
        avg_tx_per_month = features.get('avg_tx_per_month', 0)
        score += min(100, avg_tx_per_month * 10)
        
        # Card info bonus (if available)
        if card_info:
            # Add points for Etherscan reputation scores
            if 'card_credit_score' in card_info:
                score += card_info['card_credit_score'] / 10
            if 'card_zscore_reputation_score' in card_info:
                score += card_info['card_zscore_reputation_score'] / 5
        
        # Normalize to 0-1000 range
        score = max(0, min(1000, score))
        
    def calculate_scorecard_credit_score(self, features: Dict[str, Any]) -> float:
        """
        Calculate credit score using the provided scorecard bins and scores.
        Returns a single float value for credit_score.
        """
        score = 0.0

        # account_age_months (convert from account_age_days)
        account_age_days = features.get('account_age_days', 0)
        account_age_months = account_age_days / 30.0 if account_age_days > 0 else 0.0
        if account_age_months < 18.0:
            score += 54
        elif account_age_months < 54.0:
            score += 57
        else:
            score += 88

        # avg_tx_value
        avg_tx_value = features.get('avg_tx_value', 0.0)
        if avg_tx_value < 0.0006:
            score += 25
        elif avg_tx_value < 0.0181:
            score += 45
        elif avg_tx_value < 4.1449:
            score += 64
        else:
            score += 77

        # tx_count_6m
        tx_count_6m = features.get('tx_count_6m', 0)
        if tx_count_6m < 1.0:
            score += 57
        elif tx_count_6m < 3.0:
            score += 93
        else:
            score += 131

        # unique_counterparties
        unique_counterparties = features.get('unique_counterparties', 0)
        if unique_counterparties < 8.0:
            score += 49
        elif unique_counterparties < 1881.0:
            score += 60
        else:
            score += 78

        # contract_interactions
        contract_interactions = features.get('contract_interactions', 0)
        if contract_interactions < 2.0:
            score += 36
        elif contract_interactions < 19.0:
            score += 51
        elif contract_interactions < 83.0:
            score += 66
        elif contract_interactions < 1974.0:
            score += 74
        else:
            score += 84

        # largest_outgoing_tx
        largest_outgoing_tx = features.get('largest_outgoing_tx', 0.0)
        if largest_outgoing_tx < 12.8:
            score += 57
        elif largest_outgoing_tx < 206.2:
            score += 62
        else:
            score += 70

        # months_with_tx
        months_with_tx = features.get('months_with_tx', 0)
        if months_with_tx < 18.0:
            score += 59
        elif months_with_tx < 37.0:
            score += 66
        elif months_with_tx < 67.0:
            score += 68
        else:
            score += 77

        # tx_value_skewness
        tx_value_skewness = features.get('tx_value_skewness')
        if tx_value_skewness is None:
            score += 46
        elif tx_value_skewness < 4.5473:
            score += 51
        elif tx_value_skewness < 14.6823:
            score += 62
        elif tx_value_skewness < 66.3151:
            score += 67
        else:
            score += 72

        # total_transactions
        total_transactions = features.get('total_transactions', 0)
        if total_transactions < 19.0:
            score += 44
        elif total_transactions < 2508.0:
            score += 59
        elif total_transactions < 4594.0:
            score += 61
        else:
            score += 71

        return float(score)
