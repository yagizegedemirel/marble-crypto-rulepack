"""
Synthetic data generator for Marble EU Crypto AML Rule Pack.

Generates 500 customers and 10,000 transactions with controlled suspicious
patterns aligned to seven detection scenarios:

    1. High-Velocity Structuring (FATF R.10, MiCA Art. 67)
    2. Mixer/Tumbler Exposure (FATF R.15)
    3. Travel Rule Pre-Block (EU TFR 2023/1113 Art. 14)
    4. PEP Onboarding Risk (FATF R.12)
    5. Sanctioned Counterparty (OFAC/UN/EU consolidated)
    6. Smurfing Network (AMLD6 Art. 13)
    7. MASAK 5549 Cross-Border (Turkish Law no. 5549)

Output:
    customers.csv   - 500 customer records with KYC tier and risk attributes
    transactions.csv - 10,000 transactions with seeded suspicious patterns

The is_suspicious_seed flag allows scenario tests to verify detection
recall against known positives.
"""

from faker import Faker
import pandas as pd
import random
import hashlib
from datetime import datetime, timedelta

fake = Faker()
Faker.seed(42)
random.seed(42)

NUM_CUSTOMERS = 500
NUM_TRANSACTIONS = 10000
HIGH_RISK_COUNTRIES = ['IR', 'KP', 'SY', 'CU', 'MM', 'AF', 'VE']
TURKEY_CODE = 'TR'
EU_CODES = ['DE', 'FR', 'NL', 'IT', 'ES', 'BE', 'AT', 'IE']

KNOWN_MIXER_WALLETS = [
    'tc' + hashlib.sha256(f'tornado-{i}'.encode()).hexdigest()[:32]
    for i in range(20)
]

SANCTIONED_WALLETS = [
    'sx' + hashlib.sha256(f'ofac-sdn-{i}'.encode()).hexdigest()[:32]
    for i in range(15)
]


def make_customers():
    customers = []
    for i in range(NUM_CUSTOMERS):
        is_pep = random.random() < 0.02
        is_turkish = random.random() < 0.15
        country = TURKEY_CODE if is_turkish else random.choice(EU_CODES + ['US', 'GB', 'CH'])

        if random.random() < 0.01:
            country = random.choice(HIGH_RISK_COUNTRIES)

        customers.append({
            'customer_id': f'CUST-{i:04d}',
            'full_name': fake.name(),
            'country_code': country,
            'date_of_birth': fake.date_of_birth(minimum_age=18, maximum_age=75).isoformat(),
            'kyc_tier': random.choices(['tier1', 'tier2', 'tier3'], weights=[20, 60, 20])[0],
            'is_pep': is_pep,
            'risk_category': 'high' if is_pep or country in HIGH_RISK_COUNTRIES
                             else random.choices(['low', 'medium', 'high'], weights=[70, 25, 5])[0],
            'registered_at': fake.date_time_between(start_date='-2y', end_date='-1d').isoformat(),
            'email': fake.email(),
        })
    return customers


def make_transactions(customers):
    transactions = []
    structuring_customers = random.sample(customers, 12)
    mixer_customers = random.sample(customers, 8)
    sanctioned_customers = random.sample(customers, 6)
    travel_rule_customers = random.sample(customers, 20)
    smurf_ring = random.sample(customers, 15)
    masak_customers = [c for c in customers if c['country_code'] == TURKEY_CODE][:10]

    for i in range(NUM_TRANSACTIONS):
        cust = random.choice(customers)
        ts = fake.date_time_between(start_date='-30d', end_date='now')
        amount = round(random.uniform(20, 8000), 2)
        channel = random.choice(['crypto_outbound', 'crypto_inbound', 'fiat_deposit', 'fiat_withdrawal'])
        counterparty = '0x' + hashlib.sha256(f'cp-{i}'.encode()).hexdigest()[:34]
        originator_complete = True
        beneficiary_complete = True

        transactions.append({
            'transaction_id': f'TX-{i:06d}',
            'customer_id': cust['customer_id'],
            'amount_eur': amount,
            'currency': 'EUR',
            'channel': channel,
            'counterparty_identifier': counterparty,
            'counterparty_country': random.choice(EU_CODES + ['US', 'GB']),
            'originator_data_complete': originator_complete,
            'beneficiary_data_complete': beneficiary_complete,
            'timestamp': ts.isoformat(),
            'suspicious_seed': None,
        })

    # Pattern 1 - Structuring (FATF R.10): 12 customers x 6 tx, <€1,000, 24h window
    base_ts = datetime.now() - timedelta(days=5)
    for cust in structuring_customers:
        for k in range(6):
            transactions.append({
                'transaction_id': f'TX-S1-{cust["customer_id"]}-{k}',
                'customer_id': cust['customer_id'],
                'amount_eur': round(random.uniform(800, 999), 2),
                'currency': 'EUR',
                'channel': 'fiat_deposit',
                'counterparty_identifier': '0x' + hashlib.sha256(f'struct-{cust["customer_id"]}-{k}'.encode()).hexdigest()[:34],
                'counterparty_country': cust['country_code'],
                'originator_data_complete': True,
                'beneficiary_data_complete': True,
                'timestamp': (base_ts + timedelta(hours=k * 3)).isoformat(),
                'suspicious_seed': 'STRUCTURING',
            })

    # Pattern 2 - Mixer exposure (FATF R.15)
    for cust in mixer_customers:
        for k in range(2):
            transactions.append({
                'transaction_id': f'TX-S2-{cust["customer_id"]}-{k}',
                'customer_id': cust['customer_id'],
                'amount_eur': round(random.uniform(5000, 25000), 2),
                'currency': 'EUR',
                'channel': 'crypto_outbound',
                'counterparty_identifier': random.choice(KNOWN_MIXER_WALLETS),
                'counterparty_country': 'XX',
                'originator_data_complete': True,
                'beneficiary_data_complete': False,
                'timestamp': fake.date_time_between(start_date='-15d', end_date='-1d').isoformat(),
                'suspicious_seed': 'MIXER',
            })

    # Pattern 3 - Travel Rule violation (EU TFR Art. 14): >€1,000 with incomplete data
    for cust in travel_rule_customers:
        transactions.append({
            'transaction_id': f'TX-S3-{cust["customer_id"]}',
            'customer_id': cust['customer_id'],
            'amount_eur': round(random.uniform(1001, 8000), 2),
            'currency': 'EUR',
            'channel': 'crypto_outbound',
            'counterparty_identifier': '0x' + hashlib.sha256(f'tfr-{cust["customer_id"]}'.encode()).hexdigest()[:34],
            'counterparty_country': random.choice(EU_CODES),
            'originator_data_complete': False,
            'beneficiary_data_complete': random.choice([True, False]),
            'timestamp': fake.date_time_between(start_date='-20d', end_date='-1d').isoformat(),
            'suspicious_seed': 'TRAVEL_RULE',
        })

    # Pattern 5 - Sanctioned counterparty (OFAC/UN/EU)
    for cust in sanctioned_customers:
        transactions.append({
            'transaction_id': f'TX-S5-{cust["customer_id"]}',
            'customer_id': cust['customer_id'],
            'amount_eur': round(random.uniform(500, 15000), 2),
            'currency': 'EUR',
            'channel': 'crypto_outbound',
            'counterparty_identifier': random.choice(SANCTIONED_WALLETS),
            'counterparty_country': random.choice(HIGH_RISK_COUNTRIES),
            'originator_data_complete': True,
            'beneficiary_data_complete': True,
            'timestamp': fake.date_time_between(start_date='-25d', end_date='-1d').isoformat(),
            'suspicious_seed': 'SANCTIONED',
        })

    # Pattern 6 - Smurfing ring (AMLD6 Art. 13)
    funnel_wallet = '0x' + hashlib.sha256(b'smurf-funnel').hexdigest()[:34]
    base_ts = datetime.now() - timedelta(days=3)
    for idx, cust in enumerate(smurf_ring):
        for k in range(3):
            transactions.append({
                'transaction_id': f'TX-S6-{cust["customer_id"]}-{k}',
                'customer_id': cust['customer_id'],
                'amount_eur': round(random.uniform(200, 950), 2),
                'currency': 'EUR',
                'channel': 'fiat_deposit',
                'counterparty_identifier': funnel_wallet,
                'counterparty_country': cust['country_code'],
                'originator_data_complete': True,
                'beneficiary_data_complete': True,
                'timestamp': (base_ts + timedelta(hours=idx * 0.5 + k)).isoformat(),
                'suspicious_seed': 'SMURFING',
            })

    # Pattern 7 - MASAK 5549 cross-border (Turkish customer, offshore high-risk destination)
    for cust in masak_customers:
        transactions.append({
            'transaction_id': f'TX-S7-{cust["customer_id"]}',
            'customer_id': cust['customer_id'],
            'amount_eur': round(random.uniform(8000, 50000), 2),
            'currency': 'EUR',
            'channel': 'crypto_outbound',
            'counterparty_identifier': '0x' + hashlib.sha256(f'masak-{cust["customer_id"]}'.encode()).hexdigest()[:34],
            'counterparty_country': random.choice(HIGH_RISK_COUNTRIES),
            'originator_data_complete': True,
            'beneficiary_data_complete': True,
            'timestamp': fake.date_time_between(start_date='-10d', end_date='-1d').isoformat(),
            'suspicious_seed': 'MASAK_CROSSBORDER',
        })

    return transactions


def main():
    print('Generating customers...')
    customers = make_customers()
    print(f'  {len(customers)} customers generated')

    print('Generating transactions...')
    transactions = make_transactions(customers)
    print(f'  {len(transactions)} transactions generated')

    df_customers = pd.DataFrame(customers)
    df_transactions = pd.DataFrame(transactions)

    df_customers.to_csv('customers.csv', index=False)
    df_transactions.to_csv('transactions.csv', index=False)

    print('\nSuspicious pattern distribution:')
    print(df_transactions['suspicious_seed'].value_counts(dropna=False).to_string())

    print('\nFiles written:')
    print('  customers.csv')
    print('  transactions.csv')


if __name__ == '__main__':
    main()
