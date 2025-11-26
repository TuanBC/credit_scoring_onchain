"""
Off-chain data generator for wallet personas.

Generates synthetic off-chain user data independently based on wallet address.
This creates off-chain demographic and social media profiles that are separate
from on-chain behavior, providing independent data sources for credit analysis.
"""

import random
from typing import Dict, Any


class OffchainDataGenerator:
    """Generate off-chain persona data independently from on-chain features"""

    def __init__(self, seed: int = None):
        """Initialize generator with optional seed for reproducibility"""
        if seed is not None:
            random.seed(seed)

    def generate(
        self, wallet_address: str, onchain_features: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate off-chain data independently based on wallet address.

        Args:
            wallet_address: Ethereum wallet address (used for consistent seeding)
            onchain_features: Dictionary of on-chain features (not used, kept for API compatibility)

        Returns:
            Dictionary with off-chain persona data
        """
        # Use wallet address for consistent random generation
        seed = int(wallet_address[-8:], 16) % (2**31)
        rng = random.Random(seed)

        # Generate demographics independently
        age = self._generate_age(rng)
        gender = self._generate_gender(rng)
        occupation = self._generate_occupation(rng)

        # Generate income based on occupation
        monthly_income_usd = self._generate_income(occupation, age, rng)

        # Generate work experience
        years_of_experience = self._generate_experience(age, occupation, rng)
        number_of_companies = self._generate_company_count(
            years_of_experience, occupation, rng
        )

        # Generate social media metrics independently
        friend_count = self._generate_friend_count(age, rng)
        monthly_post_frequency = self._generate_post_frequency(age, occupation, rng)
        account_age_years = self._generate_social_account_age(age, rng)
        avg_reactions = self._generate_reactions(friend_count, rng)
        avg_comments = self._generate_comments(avg_reactions, rng)

        # Generate off-chain credit score independently
        offchain_credit_score = self._generate_offchain_credit_score(
            monthly_income_usd, years_of_experience, friend_count, rng
        )

        return {
            "age": age,
            "gender": gender,
            "occupation": occupation,
            "monthly_income_usd": monthly_income_usd,
            "years_of_experience": round(years_of_experience, 1),
            "number_of_companies": number_of_companies,
            "friend_count": friend_count,
            "monthly_post_frequency": round(monthly_post_frequency, 1),
            "account_age": round(account_age_years, 1),
            "average_reactions_per_post": round(avg_reactions, 1),
            "average_comments_per_post": round(avg_comments, 1),
            "offchain_credit_score": offchain_credit_score,
        }

    def _generate_age(self, rng: random.Random) -> int:
        """Generate age with normal distribution"""
        # Normal distribution centered around 35, with most people between 22-55
        age = int(rng.gauss(35, 10))
        return max(22, min(60, age))

    def _generate_gender(self, rng: random.Random) -> str:
        """Generate gender randomly with equal distribution"""
        return rng.choice(["male", "female"])

    def _generate_occupation(self, rng: random.Random) -> str:
        """Generate occupation with realistic distribution"""
        occupations = [
            ("office_worker", 0.35),  # 35%
            ("professional", 0.25),  # 25%
            ("freelancer", 0.15),  # 15%
            ("entrepreneur", 0.15),  # 15%
            ("student", 0.10),  # 10%
        ]

        # Weighted random selection
        rand = rng.random()
        cumulative = 0
        for occ, weight in occupations:
            cumulative += weight
            if rand <= cumulative:
                return occ
        return "office_worker"  # fallback

    def _generate_income(self, occupation: str, age: int, rng: random.Random) -> int:
        """Generate monthly income based on occupation and age"""
        # Base income by occupation (monthly USD)
        base_income = {
            "student": 400,
            "freelancer": 1000,
            "office_worker": 1500,
            "entrepreneur": 2500,
            "professional": 3000,
        }

        base = base_income.get(occupation, 1200)

        # Adjust by age (experience premium: 2% per year after 25)
        age_factor = 1 + ((age - 25) * 0.02)
        income = base * max(0.8, age_factor)

        # Add randomness (±20%)
        income *= rng.uniform(0.8, 1.2)

        return int(round(income / 50) * 50)  # Round to nearest 50

    def _generate_experience(
        self, age: int, occupation: str, rng: random.Random
    ) -> float:
        """Generate years of experience independently"""
        if occupation == "student":
            return round(rng.uniform(0.5, 2.5), 1)

        # Working age typically starts at 22-24
        max_experience = max(0, age - 23)

        # Generate experience as percentage of possible years (60-95%)
        experience_pct = rng.uniform(0.6, 0.95)
        experience = max_experience * experience_pct

        return max(1.0, round(experience, 1))

    def _generate_company_count(
        self, years_of_experience: float, occupation: str, rng: random.Random
    ) -> int:
        """Generate number of companies worked for independently"""
        if occupation == "student":
            return rng.choice([0, 1])

        if occupation == "freelancer":
            return rng.randint(2, 5)

        # Average 1 company per 3-4 years
        avg_years_per_company = rng.uniform(3, 4.5)
        companies = int(round(years_of_experience / avg_years_per_company))

        return max(1, min(6, companies))

    def _generate_friend_count(self, age: int, rng: random.Random) -> int:
        """Generate social media friend count independently"""
        # Base friend count with normal distribution
        base_friends = rng.gauss(250, 80)

        # Younger people tend to have slightly more online friends
        age_factor = max(0.8, 1.3 - (age - 25) / 50)
        friends = int(base_friends * age_factor)

        return max(50, min(600, friends))

    def _generate_post_frequency(
        self, age: int, occupation: str, rng: random.Random
    ) -> float:
        """Generate monthly post frequency independently"""
        # Base frequency with normal distribution (8-15 posts/month typical)
        base_frequency = rng.gauss(12, 4)

        # Age adjustment (younger = slightly more active)
        age_factor = max(0.7, 1.4 - (age - 25) / 40)
        base_frequency *= age_factor

        # Occupation adjustment
        occ_factor = {
            "student": 1.3,
            "freelancer": 1.2,
            "office_worker": 1.0,
            "entrepreneur": 1.1,
            "professional": 0.9,
        }
        base_frequency *= occ_factor.get(occupation, 1.0)

        return max(3.0, min(40.0, base_frequency))

    def _generate_social_account_age(self, age: int, rng: random.Random) -> float:
        """Generate social media account age in years independently"""
        # Account age typically 3-10 years for active users
        max_account_age = min(age - 18, 12)
        account_age = rng.uniform(2.5, max(3, max_account_age))

        return max(1.0, min(15.0, account_age))

    def _generate_reactions(self, friend_count: int, rng: random.Random) -> float:
        """Generate average reactions per post independently"""
        # Base reactions: roughly 5-10% of friend count engage
        engagement_rate = rng.uniform(0.05, 0.12)
        base_reactions = friend_count * engagement_rate

        # Add randomness
        reactions = base_reactions * rng.uniform(0.7, 1.3)

        return max(8.0, min(60.0, reactions))

    def _generate_comments(self, avg_reactions: float, rng: random.Random) -> float:
        """Generate average comments per post (typically lower than reactions)"""
        # Comments are typically 40-70% of reactions
        comments = avg_reactions * rng.uniform(0.4, 0.7)

        return max(2.0, min(30.0, comments))

    def _generate_offchain_credit_score(
        self,
        monthly_income: int,
        years_experience: float,
        friend_count: int,
        rng: random.Random,
    ) -> int:
        """Generate off-chain credit score independently (300-850)"""
        base_score = 650

        # Income factor (+0 to +80)
        income_bonus = min(80, (monthly_income / 30))

        # Experience factor (+0 to +40)
        exp_bonus = min(40, years_experience * 4)

        # Social factor (+0 to +30)
        social_bonus = min(30, (friend_count / 15))

        # Calculate total
        score = base_score + income_bonus + exp_bonus + social_bonus

        # Add randomness (±30 points)
        score += rng.uniform(-30, 30)

        # Clamp to realistic credit score range (300-850)
        score = max(300, min(850, score))

        return int(round(score / 10) * 10)  # Round to nearest 10
