"""
BEAM 데이터가 평일인지 주말인지 판별하는 스크립트
- baseDate 확인
- Population 활동 패턴 분석
- 충전 이벤트 시간 분포 분석
"""

import gzip
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from collections import Counter
import pandas as pd

def check_base_date(config_file):
    """설정 파일에서 baseDate 확인"""
    print("\n" + "="*80)
    print("📅 1. BEAM 설정 파일의 baseDate 확인")
    print("="*80)

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            for line in f:
                if 'baseDate' in line and not line.strip().startswith('#'):
                    print(f"설정 라인: {line.strip()}")

                    # ISO 8601 날짜 추출
                    if '"' in line:
                        date_str = line.split('"')[1].split('T')[0]
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                        weekday = date_obj.strftime('%A')
                        weekday_ko = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일'][date_obj.weekday()]

                        print(f"\n📆 시뮬레이션 시작 날짜: {date_str}")
                        print(f"📆 요일: {weekday} ({weekday_ko})")

                        if date_obj.weekday() < 5:
                            print(f"✅ 평일 데이터 (월~금)")
                        else:
                            print(f"✅ 주말 데이터 (토~일)")

                        return date_obj
    except Exception as e:
        print(f"⚠️ 설정 파일을 읽을 수 없습니다: {e}")

    return None

def analyze_population_activities(population_file):
    """Population 파일의 활동 타입 분포 분석"""
    print("\n" + "="*80)
    print("📊 2. Population 활동 패턴 분석")
    print("="*80)

    try:
        with gzip.open(population_file, 'rt') as f:
            tree = ET.parse(f)
            root = tree.getroot()

            activity_types = []
            activity_times = []

            for person in root.findall('.//person')[:500]:  # 샘플링
                for plan in person.findall('.//plan'):
                    for activity in plan.findall('.//activity'):
                        act_type = activity.get('type')
                        if act_type:
                            activity_types.append(act_type)

                        # 시작 시간 분석
                        end_time = activity.get('end_time')
                        if end_time:
                            h = int(end_time.split(':')[0])
                            activity_times.append(h)

            # 활동 타입 분포
            type_counts = Counter(activity_types)
            total = sum(type_counts.values())

            print("\n📈 활동 타입 분포:")
            for act_type, count in type_counts.most_common(10):
                percentage = (count / total) * 100
                print(f"  {act_type:<20}: {count:>6} ({percentage:>5.1f}%)")

            # 평일/주말 판별
            work_school_ratio = (type_counts.get('Work', 0) + type_counts.get('work', 0) +
                                type_counts.get('School', 0) + type_counts.get('school', 0)) / total

            print(f"\n💼 Work/School 활동 비율: {work_school_ratio:.1%}")

            if work_school_ratio > 0.2:
                print("✅ 평일 패턴 (직장/학교 활동이 많음)")
            else:
                print("✅ 주말 패턴 (여가 활동이 많음)")

            # 시간대 분포
            time_counts = Counter(activity_times)
            morning_peak = sum(time_counts.get(h, 0) for h in range(7, 10))
            evening_peak = sum(time_counts.get(h, 0) for h in range(17, 20))

            print(f"\n🕐 출근 시간대(07-09시) 활동: {morning_peak}")
            print(f"🕐 퇴근 시간대(17-19시) 활동: {evening_peak}")

    except Exception as e:
        print(f"⚠️ Population 파일 분석 실패: {e}")

def analyze_charging_events(events_file):
    """충전 이벤트 시간 분포로 평일/주말 추론"""
    print("\n" + "="*80)
    print("🔌 3. 충전 이벤트 시간 패턴 분석")
    print("="*80)

    try:
        # CSV 파일 로드
        df = pd.read_csv(events_file)

        # ChargingPlugIn 이벤트만 필터링
        charging = df[df['type'] == 'ChargingPlugInEvent'].copy()

        if len(charging) == 0:
            print("⚠️ 충전 이벤트가 없습니다.")
            return

        print(f"\n📊 총 충전 이벤트: {len(charging)}개")

        # 시간대별 분포
        charging['hour'] = (charging['time'] / 3600).astype(int) % 24
        hourly = charging.groupby('hour').size()

        print("\n🕐 시간대별 충전 횟수:")
        for hour in range(24):
            count = hourly.get(hour, 0)
            bar = '█' * int(count / max(hourly) * 30)
            print(f"  {hour:02d}시: {bar} ({count})")

        # 피크 시간대 확인
        morning_peak = hourly[hourly.index.isin(range(7, 10))].sum()
        evening_peak = hourly[hourly.index.isin(range(17, 20))].sum()
        night = hourly[hourly.index.isin(range(22, 24)) | hourly.index.isin(range(0, 6))].sum()

        print(f"\n📈 충전 패턴 분석:")
        print(f"  출근 시간대(07-09시): {morning_peak}회")
        print(f"  퇴근 시간대(17-19시): {evening_peak}회")
        print(f"  야간(22-06시): {night}회")

        if evening_peak > morning_peak and evening_peak > night:
            print("\n✅ 평일 패턴 (퇴근 후 가정 충전 피크)")
        elif night > evening_peak:
            print("\n✅ 평일 또는 주말 (야간 충전 선호)")
        else:
            print("\n✅ 주말 패턴 (균등 분포)")

    except Exception as e:
        print(f"⚠️ 이벤트 파일 분석 실패: {e}")

def main():
    base_path = Path('.')

    print("\n" + "="*80)
    print("🔍 BEAM 데이터 평일/주말 판별 분석")
    print("="*80)

    # 1. baseDate 확인
    config_file = base_path / 'test/input/sf-light/sf-light-1k.conf'
    if config_file.exists():
        base_date = check_base_date(config_file)
    else:
        print(f"⚠️ 설정 파일을 찾을 수 없습니다: {config_file}")
        base_date = None

    # 2. Population 분석
    pop_file = base_path / 'test/input/sf-light/sample/1k/population.xml.gz'
    if pop_file.exists():
        analyze_population_activities(pop_file)
    else:
        print(f"⚠️ Population 파일을 찾을 수 없습니다: {pop_file}")

    # 3. 충전 이벤트 분석
    events_files = list(base_path.glob('output/sf-light/**/ITERS/it.*/5.events.csv'))
    if not events_files:
        events_files = list(base_path.glob('output/sf-light/**/ITERS/it.*/0.events.csv'))

    if events_files:
        print(f"\n📁 이벤트 파일 발견: {events_files[0]}")
        analyze_charging_events(events_files[0])
    else:
        print("\n⚠️ 이벤트 파일을 찾을 수 없습니다.")

    # 최종 결론
    print("\n" + "="*80)
    print("📋 결론")
    print("="*80)
    if base_date:
        if base_date.weekday() < 5:
            print("✅ 현재 데이터는 **평일** 데이터입니다.")
            print(f"   시작: {base_date.strftime('%A, %Y-%m-%d')} (평일)")
            print(f"   1.27일 = 약 30.5시간 = 다음날 새벽까지 (여전히 평일)")
        else:
            print("✅ 현재 데이터는 **주말** 데이터입니다.")
            print(f"   시작: {base_date.strftime('%A, %Y-%m-%d')} (주말)")
    else:
        print("⚠️ baseDate를 확인할 수 없어 정확한 판단이 어렵습니다.")

    print("\n💡 7일 데이터 생성 시 고려사항:")
    if base_date and base_date.weekday() < 5:
        print("  - 현재: 월요일 데이터 (평일)")
        print("  - 확장: 월(기존) + 화수목금(복제) + 토일(가중치 조정)")
        print("  - 주말 가중치: 충전 +15~20% (가정 충전 증가)")
    else:
        print("  - 데이터 타입에 따라 적절히 확장")

if __name__ == '__main__':
    main()