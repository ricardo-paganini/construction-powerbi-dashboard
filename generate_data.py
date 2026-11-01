import random
import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

reference_date = pd.Timestamp('2025-12-31')

# Empreendimentos
developments = pd.DataFrame({
    'development_id': ['D01', 'D02', 'D03', 'D04', 'D05', 'D06', 'D07', 'D08'],
    'development_name': ['Residencial Jardim das Flores', 'Edifício Mirante', 'Residencial Parque Verde',
                         'Edifício Solar do Vale', 'Residencial Bela Vista', 'Edifício Horizonte',
                         'Residencial Recanto', 'Edifício Alto da Serra'],
    'city': ['Campinas', 'Campinas', 'Sorocaba', 'São José dos Campos',
             'Sorocaba', 'São José dos Campos', 'Campinas', 'Sorocaba'],
    'standard': ['Econômico', 'Alto', 'Econômico', 'Médio', 'Médio', 'Econômico', 'Médio', 'Alto'],
    'launch_date': pd.to_datetime(['2022-03-01', '2022-08-01', '2023-01-01', '2023-05-01',
                                   '2023-09-01', '2024-01-01', '2024-04-01', '2024-09-01']),
})

units_by_standard = {'Econômico': (140, 200), 'Médio': (80, 120), 'Alto': (40, 60)}
developments['total_units'] = [random.randint(*units_by_standard[s]) for s in developments['standard']]
developments['expected_delivery'] = [d + pd.DateOffset(months=random.choice([30, 33, 36]))
                                     for d in developments['launch_date']]

# Unidades
typology_mix = {'Econômico': [0.45, 0.50, 0.05], 'Médio': [0.15, 0.55, 0.30], 'Alto': [0.0, 0.40, 0.60]}
area_by_typology = {
    'Econômico': {'1 dormitório': 38, '2 dormitórios': 48, '3 dormitórios': 62},
    'Médio': {'1 dormitório': 45, '2 dormitórios': 62, '3 dormitórios': 80},
    'Alto': {'1 dormitório': 60, '2 dormitórios': 85, '3 dormitórios': 120},
}
price_m2 = {'Econômico': 5500, 'Médio': 8000, 'Alto': 12000}
cost_m2 = {'Econômico': 3000, 'Médio': 3800, 'Alto': 5200}

unit_rows = []
for _, dev in developments.iterrows():
    for n in range(1, dev['total_units'] + 1):
        typology = np.random.choice(['1 dormitório', '2 dormitórios', '3 dormitórios'], p=typology_mix[dev['standard']])
        area = round(area_by_typology[dev['standard']][typology] * np.random.uniform(0.95, 1.05), 1)
        price = round(area * price_m2[dev['standard']] * np.random.uniform(0.95, 1.10), -2)
        unit_rows.append([f"{dev['development_id']}-{n:03d}", dev['development_id'], typology, area, price])

units = pd.DataFrame(unit_rows, columns=['unit_id', 'development_id', 'typology', 'area_m2', 'list_price'])

# Orçamento da obra = área total x custo por m²
total_area = units.groupby('development_id')['area_m2'].sum()
developments['budget'] = [round(total_area[d] * cost_m2[s], -3)
                          for d, s in zip(developments['development_id'], developments['standard'])]

# Vendas
channels = ['Imobiliária parceira', 'Plantão de vendas', 'Digital']
channel_probs = [0.45, 0.30, 0.25]
dev_info = developments.set_index('development_id')

sale_rows = []
sale_id = 1
for _, unit in units.iterrows():
    dev = dev_info.loc[unit['development_id']]
    months_available = (reference_date.year - dev['launch_date'].year) * 12 + reference_date.month - dev['launch_date'].month
    sell_prob = min(0.95, 0.30 + months_available * 0.025)
    if random.random() > sell_prob:
        continue
    # Vendas concentradas no começo (lançamento)
    month_offset = min(int(np.random.exponential(months_available / 3)), months_available)
    sale_date = dev['launch_date'] + pd.DateOffset(months=month_offset, days=random.randint(0, 27))
    channel = np.random.choice(channels, p=channel_probs)
    sale_value = round(unit['list_price'] * (1 - np.random.uniform(0, 0.08)), -2)

    cancel_prob = 0.06
    if channel == 'Digital':
        cancel_prob += 0.12
    if dev['standard'] == 'Econômico':
        cancel_prob += 0.08
    cancelled = random.random() < cancel_prob
    cancel_date = sale_date + pd.DateOffset(days=random.randint(30, 400)) if cancelled else pd.NaT
    if cancelled and cancel_date > reference_date:
        cancelled, cancel_date = False, pd.NaT

    sale_rows.append([f'V{sale_id:05d}', unit['unit_id'], sale_date, sale_value, channel,
                      'Distratada' if cancelled else 'Ativa', cancel_date])
    sale_id += 1

sales = pd.DataFrame(sale_rows, columns=['sale_id', 'unit_id', 'sale_date', 'sale_value',
                                         'channel', 'status', 'cancel_date'])

# Custos e avanço físico da obra
stages = {'Fundação': (0.00, 0.20, 0.12), 'Estrutura': (0.10, 0.55, 0.30), 'Alvenaria': (0.35, 0.75, 0.15),
          'Instalações': (0.45, 0.90, 0.18), 'Acabamento': (0.65, 1.00, 0.25)}
stage_overrun = {'Fundação': 0.03, 'Estrutura': 0.15, 'Alvenaria': 0.02, 'Instalações': 0.05, 'Acabamento': 0.04}
problem_developments = {'D03': 0.12, 'D06': 0.15, 'D04': 0.06}

cost_rows = []
progress_rows = []
for _, dev in developments.iterrows():
    start = dev['launch_date'] + pd.DateOffset(months=3)
    months = pd.date_range(start, dev['expected_delivery'], freq='MS')
    total_months = len(months)
    dev_overrun = problem_developments.get(dev['development_id'], 0)
    efficiency = 1 - dev_overrun * 1.5
    realized_cum = 0

    for i, month in enumerate(months):
        if month > reference_date:
            break
        position = (i + 1) / total_months
        for stage, (begin, end, weight) in stages.items():
            if begin <= position <= end + 1e-9:
                stage_months = max(1, round((end - begin) * total_months))
                budgeted = dev['budget'] * weight / stage_months
                realized = budgeted * (1 + stage_overrun[stage] + dev_overrun) * np.random.uniform(0.90, 1.10)
                cost_rows.append([dev['development_id'], month, stage, round(budgeted, 2), round(realized, 2)])

        planned_cum = round(100 * (3 * position ** 2 - 2 * position ** 3), 1)
        realized_cum = min(100, max(realized_cum, planned_cum * efficiency * np.random.uniform(0.97, 1.02)))
        progress_rows.append([dev['development_id'], month, planned_cum, round(realized_cum, 1)])

    # Obra atrasada continua depois da data prevista até terminar
    month = months[-1] + pd.DateOffset(months=1)
    while realized_cum < 100 and month <= reference_date:
        realized_cum = min(100, realized_cum + np.random.uniform(3, 5))
        progress_rows.append([dev['development_id'], month, 100.0, round(realized_cum, 1)])
        month += pd.DateOffset(months=1)

construction_costs = pd.DataFrame(cost_rows, columns=['development_id', 'month', 'stage',
                                                      'budgeted_cost', 'actual_cost'])
construction_progress = pd.DataFrame(progress_rows, columns=['development_id', 'month',
                                                             'planned_progress', 'actual_progress'])

# Problemas de qualidade
city_variants = {'São José dos Campos': 'Sao Jose dos Campos', 'Campinas': 'campinas ', 'Sorocaba': 'SOROCABA'}
for i in [1, 3, 4]:
    developments.loc[i, 'city'] = city_variants[developments.loc[i, 'city']]

channel_variants = {'Digital': ['digital', 'DIGITAL', 'Online'],
                    'Imobiliária parceira': ['imobiliaria parceira', 'Imobiliária'],
                    'Plantão de vendas': ['plantao de vendas', 'Plantão']}
for idx in sales.sample(frac=0.08, random_state=42).index:
    sales.loc[idx, 'channel'] = random.choice(channel_variants[sales.loc[idx, 'channel']])
sales.loc[sales.sample(n=18, random_state=1).index, 'channel'] = np.nan
sales.loc[sales.sample(n=6, random_state=2).index, 'sale_value'] = np.nan

cancelled_idx = sales[sales['status'] == 'Distratada'].sample(n=5, random_state=3).index
sales.loc[cancelled_idx, 'cancel_date'] = sales.loc[cancelled_idx, 'sale_date'] - pd.DateOffset(days=45)

sales = pd.concat([sales, sales.sample(n=22, random_state=4)]).sort_values('sale_id').reset_index(drop=True)

construction_costs.loc[construction_costs.sample(n=4, random_state=5).index, 'actual_cost'] *= -1
construction_costs.loc[construction_costs.sample(n=5, random_state=6).index, 'actual_cost'] = np.nan
construction_costs = pd.concat([construction_costs, construction_costs.sample(n=10, random_state=7)]).reset_index(drop=True)

# Salvando
developments.to_csv('developments.csv', index=False)
units.to_csv('units.csv', index=False)
sales.to_csv('sales.csv', index=False)
construction_costs.to_csv('construction_costs.csv', index=False)
construction_progress.to_csv('construction_progress.csv', index=False)

print('Bases geradas com sucesso!')