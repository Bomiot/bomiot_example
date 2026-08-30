"""
Bomiot 营收模型生成器

- 读取同级目录下的 parameters.csv
- 在同级目录下生成 revenue_model.csv 和 Bomiot_revenue_model.xlsx
- 基于月度队列模型计算设备增长、流失和累计营收

依赖: pandas, openpyxl
运行: python test.py
"""

import pandas as pd
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_CSV = SCRIPT_DIR / 'revenue_model.csv'
OUT_XLSX = SCRIPT_DIR / 'Bomiot_revenue_model.xlsx'

def find_parameters_file():
    candidates = [
        SCRIPT_DIR / 'parameters.csv',
        Path.cwd() / 'parameters.csv',
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        "Missing parameters.csv. Searched:\n" +
        "\n".join(str(p) for p in candidates)
    )

def load_parameters():
    param_path = find_parameters_file()
    print(f"Loading parameters from: {param_path}")
    df = pd.read_csv(param_path)
    return df.to_dict(orient='records')

def run_model(params, months=36):
    rows = []
    devices_prev = 0.0
    cumulative_revenue = 0.0
    marketing_devices = float(params.get('marketing_devices', 0))
    marketing_months = int(params.get('marketing_months', 0))
    pricing_model = params.get('pricing_model', 'subscription')
    buyout_price = float(params.get('buyout_price', 0))
    renewal_rate = float(params.get('renewal_rate', 0))
    price = float(params.get('price', 0))

    for t in range(1, months+1):
        organic_new = round(params['new0'] * ((1.0 + params['growth']) ** (t-1)), 2)
        marketing_new = 0.0
        if marketing_devices > 0 and t <= marketing_months:
            marketing_new = marketing_devices
        new_t = round(organic_new + marketing_new, 2)
        devices_t = round(devices_prev * (1.0 - params['churn']) + new_t, 2)

        if pricing_model == 'subscription':
            monthly_revenue = round(devices_t * price, 2)
            one_time_revenue = 0.0
            renewal_revenue = 0.0
        else:
            one_time_revenue = round(new_t * buyout_price, 2)
            monthly_revenue = 0.0
            # 续费：每年有 renewal_rate 比例的设备续费，按月摊销
            renewal_monthly = 0.0
            if t > 12:
                devices_12_months_ago = 0.0
                # 近似：上一年同期的设备数
                if t - 12 > 0:
                    pass  # 简化处理
                renewal_monthly = round(devices_t * renewal_rate * buyout_price / 12, 2)
            renewal_revenue = renewal_monthly

        monthly_total = round(monthly_revenue + one_time_revenue + renewal_revenue, 2)
        cumulative_revenue = round(cumulative_revenue + monthly_total, 2)

        rows.append({
            '月份': t,
            '定价模式': '订阅' if pricing_model == 'subscription' else '买断',
            '自然增长': organic_new,
            '推广增长': marketing_new,
            '新增设备': new_t,
            '设备总数': devices_t,
            '订阅营收': monthly_revenue,
            '买断营收': one_time_revenue,
            '续费营收': renewal_revenue,
            '月总营收': monthly_total,
            '累计营收': cumulative_revenue,
        })
        devices_prev = devices_t
    return pd.DataFrame(rows)


def main():
    params_list = load_parameters()
    months = int(params_list[0].get('months', 36))

    scenario_dfs = {}
    for p in params_list:
        name = p['scenario']
        df = run_model(p, months=months)
        scenario_dfs[name] = df

    # create combined CSV with columns for each scenario side-by-side
    combined = None
    for name, df in scenario_dfs.items():
        df = df.copy()
        # rename columns with suffix
        suf = '_' + name
        df_renamed = df.rename(columns={
            '定价模式': '定价模式' + suf,
            '自然增长': '自然增长' + suf,
            '推广增长': '推广增长' + suf,
            '新增设备': '新增设备' + suf,
            '设备总数': '设备总数' + suf,
            '订阅营收': '订阅营收' + suf,
            '买断营收': '买断营收' + suf,
            '续费营收': '续费营收' + suf,
            '月总营收': '月总营收' + suf,
            '累计营收': '累计营收' + suf,
        })
        if combined is None:
            combined = df_renamed
        else:
            df_renamed = df_renamed.drop(columns=['月份'])
            combined = pd.concat([combined, df_renamed], axis=1)

    combined.to_csv(OUT_CSV, index=False, encoding='utf-8-sig')

    # write Excel with a sheet per scenario + parameters
    with pd.ExcelWriter(OUT_XLSX, engine='openpyxl') as writer:
        params_df = pd.DataFrame(params_list)
        params_df.to_excel(writer, sheet_name='参数', index=False)
        for name, df in scenario_dfs.items():
            df.to_excel(writer, sheet_name=name, index=False)
        combined.to_excel(writer, sheet_name='汇总', index=False)

    print(f'Wrote: {OUT_CSV} and {OUT_XLSX}')

if __name__ == '__main__':
    main()
