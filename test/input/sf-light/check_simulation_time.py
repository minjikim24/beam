import pandas as pd

# 이벤트 파일 로드
df = pd.read_csv('output\sf-light\sf-light-1k-xml__2025-11-13_02-51-59_msa/ITERS/it.5/5.events.csv')

print(f'📊 시뮬레이션 시간 범위: {df["time"].min():.0f} ~ {df["time"].max():.0f} 초')
print(f'📅 총 일수: {df["time"].max() / 86400:.2f} 일')
print(f'🔢 총 이벤트 수: {len(df):,} 개')

# 충전 이벤트 분석
charging = df[df['type'] == 'ChargingPlugInEvent']
if len(charging) > 0:
    print(f'\n⚡ 충전 이벤트: {len(charging)} 개')
    print(f'📆 충전 시간 범위: {charging["time"].min() / 86400:.2f} ~ {charging["time"].max() / 86400:.2f} 일')

    # 일별 충전 횟수
    charging['day'] = (charging['time'] / 86400).astype(int)
    daily_count = charging.groupby('day').size()
    print(f'\n📋 일별 충전 횟수:')
    for day, count in daily_count.items():
        print(f'  Day {day}: {count} 회')
    print(f'\n총 {len(daily_count)} 일간 충전 발생')