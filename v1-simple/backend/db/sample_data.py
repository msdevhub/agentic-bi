"""生成 AIA 保险行业示例数据 — 4张表 (policies, claims, agents, renewals)"""
import random
import datetime
import duckdb
from pathlib import Path

DB_PATH = Path(__file__).parent / "data.duckdb"

# AIA 保险业务维度
REGIONS = ["华东", "华南", "华北", "华中", "西南", "西北", "东北", "港澳"]
CHANNELS = ["代理人", "银保", "电销", "互联网", "经纪", "团险直销"]
PRODUCT_TYPES = ["寿险", "健康险", "意外险", "年金险", "投连险", "万能险"]
PRODUCT_NAMES = {
    "寿险": ["友邦传世", "如意人生", "全佑一生"],
    "健康险": ["友邦重疾", "全佑惠享", "守护丽人"],
    "意外险": ["友邦百万", "安心保", "出行无忧"],
    "年金险": ["友邦金账户", "稳赢人生", "充裕未来"],
    "投连险": ["智选投资", "进取投资", "稳健投资"],
    "万能险": ["友邦万能", "财富管家", "灵活宝"],
}

STATUS_LIST = ["有效", "退保", "满期", "理赔中"]

# 代理人数据
AGENT_LEVELS = ["初级", "中级", "高级", "总监"]
AGENT_STATUSES = ["在职", "离职", "停牌"]

random.seed(42)


def generate():
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = duckdb.connect(str(DB_PATH))
    start = datetime.date(2022, 1, 1)
    end = datetime.date(2025, 12, 31)
    delta_days = (end - start).days

    # ==================== agents (代理人) ====================
    conn.execute("""
        CREATE TABLE agents (
            agent_id VARCHAR,
            agent_name VARCHAR,
            region VARCHAR,
            team VARCHAR,
            level VARCHAR,
            join_date DATE,
            agent_status VARCHAR,
            total_premium DOUBLE,
            policy_count INTEGER,
            customer_count INTEGER
        )
    """)

    last_names = "王李张刘陈杨赵黄周吴徐孙胡朱高林何郭马罗"
    first_names = "伟芳娜秀英敏静丽强磊洋勇艳杰娟涛明超秀兰霞"
    teams = ["精英A队", "精英B队", "金牌团队", "新星团队", "卓越团队", "先锋团队"]

    agent_rows = []
    for i in range(500):
        region = random.choice(REGIONS)
        name = random.choice(last_names) + random.choice(first_names) + random.choice(first_names)
        team = random.choice(teams)
        level = random.choices(AGENT_LEVELS, weights=[40, 30, 20, 10])[0]
        join_dt = start + datetime.timedelta(days=random.randint(0, delta_days))
        status = random.choices(AGENT_STATUSES, weights=[75, 20, 5])[0]
        total_prem = round(random.uniform(50000, 5000000), 2)
        policy_cnt = random.randint(10, 500)
        cust_cnt = random.randint(8, 400)

        agent_rows.append((
            f"AGT{i:05d}", name, region, team, level,
            str(join_dt), status, total_prem, policy_cnt, cust_cnt,
        ))

    conn.executemany("INSERT INTO agents VALUES (?,?,?,?,?,?,?,?,?,?)", agent_rows)

    # ==================== policies (保单) ====================
    conn.execute("""
        CREATE TABLE policies (
            policy_id VARCHAR,
            policy_date DATE,
            region VARCHAR,
            channel VARCHAR,
            product_type VARCHAR,
            product_name VARCHAR,
            premium DOUBLE,
            sum_insured DOUBLE,
            commission DOUBLE,
            policy_status VARCHAR,
            customer_age INTEGER,
            customer_gender VARCHAR,
            payment_years INTEGER,
            is_new_business BOOLEAN,
            agent_id VARCHAR
        )
    """)

    policy_rows = []
    for i in range(8000):
        dt = start + datetime.timedelta(days=random.randint(0, delta_days))
        region = random.choice(REGIONS)
        channel = random.choice(CHANNELS)
        product_type = random.choice(PRODUCT_TYPES)
        product_name = random.choice(PRODUCT_NAMES[product_type])

        base_premium = {
            "寿险": (8000, 50000), "健康险": (3000, 25000), "意外险": (500, 5000),
            "年金险": (10000, 100000), "投连险": (20000, 200000), "万能险": (15000, 80000),
        }[product_type]
        premium = round(random.uniform(*base_premium), 2)
        sum_insured = round(premium * random.uniform(5, 30), 2)
        commission = round(premium * random.uniform(0.05, 0.35), 2)

        age = random.randint(22, 65)
        gender = random.choice(["男", "女"])
        payment_years = random.choice([1, 3, 5, 10, 15, 20])
        status = random.choices(STATUS_LIST, weights=[75, 10, 8, 7])[0]
        is_new = dt.year >= 2024 or random.random() < 0.3

        # 代理人渠道关联 agent_id
        agent_id = None
        if channel == "代理人":
            region_agents = [a for a in agent_rows if a[2] == region]
            if region_agents:
                agent_id = random.choice(region_agents)[0]

        policy_rows.append((
            f"AIA{dt.year}{i:06d}",
            str(dt), region, channel, product_type, product_name,
            premium, sum_insured, commission, status,
            age, gender, payment_years, is_new, agent_id,
        ))

    conn.executemany(
        "INSERT INTO policies VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        policy_rows,
    )

    # ==================== claims (理赔) ====================
    conn.execute("""
        CREATE TABLE claims (
            claim_id VARCHAR,
            claim_date DATE,
            policy_id VARCHAR,
            region VARCHAR,
            product_type VARCHAR,
            claim_type VARCHAR,
            claim_amount DOUBLE,
            paid_amount DOUBLE,
            claim_status VARCHAR,
            processing_days INTEGER
        )
    """)

    claim_types = ["重疾", "住院", "身故", "意外医疗", "门诊", "残疾"]
    claim_statuses = ["已结案", "审核中", "已拒赔", "待补充材料"]
    # 按险种设定合理的理赔金额范围（与保费匹配）
    claim_amount_ranges = {
        "寿险": (5000, 80000),      # 寿险保费 8K-50K
        "健康险": (2000, 50000),    # 健康险保费 3K-25K
        "意外险": (500, 8000),      # 意外险保费 500-5K
    }
    claim_rows = []
    for i in range(3000):
        dt = start + datetime.timedelta(days=random.randint(0, delta_days))
        region = random.choice(REGIONS)
        product_type = random.choice(["寿险", "健康险", "意外险"])
        claim_type = random.choice(claim_types)
        amt_range = claim_amount_ranges[product_type]
        claim_amount = round(random.uniform(*amt_range), 2)
        paid_ratio = random.uniform(0.5, 1.0) if random.random() > 0.15 else 0
        paid_amount = round(claim_amount * paid_ratio, 2)
        status = random.choices(claim_statuses, weights=[60, 20, 10, 10])[0]
        days = random.randint(1, 90)

        # 关联同险种的保单
        same_type = [j for j, p in enumerate(policy_rows) if p[4] == product_type]
        policy_idx = random.choice(same_type) if same_type else random.randint(0, len(policy_rows) - 1)
        policy_id = policy_rows[policy_idx][0]

        claim_rows.append((
            f"CLM{dt.year}{i:06d}",
            str(dt), policy_id, region, product_type, claim_type,
            claim_amount, paid_amount, status, days,
        ))

    conn.executemany(
        "INSERT INTO claims VALUES (?,?,?,?,?,?,?,?,?,?)",
        claim_rows,
    )

    # ==================== renewals (续保记录) ====================
    conn.execute("""
        CREATE TABLE renewals (
            renewal_id VARCHAR,
            policy_id VARCHAR,
            renewal_date DATE,
            renewal_year INTEGER,
            renewal_premium DOUBLE,
            renewal_status VARCHAR,
            lapse_reason VARCHAR
        )
    """)

    renewal_statuses = ["已续保", "已失效", "宽限期"]
    lapse_reasons = [None, "未缴费", "客户主动退保", "银行扣款失败", "保费过高"]
    renewal_rows = []
    idx = 0
    for p in policy_rows:
        policy_id = p[0]
        policy_date = datetime.date.fromisoformat(p[1])
        premium = p[6]
        payment_years = p[12]

        # 每个保单每年一条续保记录（从第2年起）
        for yr in range(1, min(payment_years, 4)):
            r_date = policy_date + datetime.timedelta(days=365 * yr)
            if r_date > end:
                break
            r_status = random.choices(renewal_statuses, weights=[80, 12, 8])[0]
            reason = None
            if r_status == "已失效":
                reason = random.choice([r for r in lapse_reasons if r])
            r_premium = round(premium * random.uniform(0.95, 1.05), 2)

            renewal_rows.append((
                f"RNW{idx:07d}", policy_id, str(r_date), r_date.year,
                r_premium, r_status, reason,
            ))
            idx += 1
            if idx >= 12000:
                break
        if idx >= 12000:
            break

    conn.executemany(
        "INSERT INTO renewals VALUES (?,?,?,?,?,?,?)",
        renewal_rows,
    )

    conn.close()
    print(f"✅ 数据生成完成:")
    print(f"   agents:   {len(agent_rows)} 行")
    print(f"   policies: {len(policy_rows)} 行")
    print(f"   claims:   {len(claim_rows)} 行")
    print(f"   renewals: {len(renewal_rows)} 行")


if __name__ == "__main__":
    generate()
