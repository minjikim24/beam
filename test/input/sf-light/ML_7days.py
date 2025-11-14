"""
BEAM 충전 데이터 7일 확장 스크립트
- 1.27일 월요일 평일 데이터를 7일로 확장
- 평일(월-금) vs 주말(토-일) 차별화
- ML 학습용 Feature 생성
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

class ChargingDataExpander:
    def __init__(self, events_file):
        """
        Args:
            events_file: BEAM events.csv 파일 경로
        """
        self.events_file = events_file
        self.base_date = datetime(2019, 4, 1)  # 월요일
        self.charging_data = None
        self.expanded_data = None

    def load_data(self):
        """충전 이벤트 데이터 로드"""
        print("📂 데이터 로딩 중...")

        # CSV 로드 (dtype 경고 억제)
        df = pd.read_csv(self.events_file, low_memory=False)

        # ChargingPlugIn 이벤트만 필터링
        charging = df[df['type'] == 'ChargingPlugInEvent'].copy()

        print(f"✅ 총 {len(charging)}개 충전 이벤트 로드")

        # 필요한 컬럼만 추출
        self.charging_data = charging[['time', 'vehicle', 'locationX', 'locationY']].copy()
        self.charging_data['time'] = self.charging_data['time'].astype(float)

        # 시간 관련 컬럼 생성
        self.charging_data['hour'] = (self.charging_data['time'] / 3600) % 24
        self.charging_data['day'] = (self.charging_data['time'] / 86400).astype(int)

        return self.charging_data

    def analyze_hourly_pattern(self):
        """시간대별 충전 패턴 분석"""
        print("\n📊 시간대별 패턴 분석 중...")

        hourly_counts = self.charging_data.groupby('hour').size()
        hourly_pattern = (hourly_counts / hourly_counts.sum()).to_dict()

        print("\n시간대별 충전 비율:")
        for hour in sorted(hourly_pattern.keys()):
            percentage = hourly_pattern[hour] * 100
            bar = '█' * int(percentage * 2)
            print(f"  {int(hour):02d}시: {bar} {percentage:.1f}%")

        return hourly_pattern

    def expand_to_7days(self, weekend_multiplier=1.15):
        """
        1일 데이터를 7일로 확장

        Args:
            weekend_multiplier: 주말 충전 증가율 (기본 15%)
        """
        print(f"\n🔄 7일 데이터 확장 중 (주말 가중치: {weekend_multiplier:.1%})...")

        # 시간대별 패턴 추출
        hourly_pattern = self.charging_data.groupby(self.charging_data['hour'].astype(int)).size()

        expanded_records = []

        for day in range(7):
            # 요일 결정 (0=월요일, 6=일요일)
            weekday = day % 7
            is_weekend = weekday >= 5

            # 주말 가중치 적용
            if is_weekend:
                day_multiplier = weekend_multiplier
            else:
                day_multiplier = 1.0

            # 평일/주말에 따른 시간대별 패턴 조정
            for hour in range(24):
                # 기본 충전 횟수 (패턴 기반)
                base_count = hourly_pattern.get(hour, 0)

                # 주말 시간대별 차별화
                if is_weekend:
                    if 7 <= hour <= 9:  # 출근 시간대 - 감소
                        hour_multiplier = 0.5
                    elif 17 <= hour <= 19:  # 퇴근 시간대 - 감소
                        hour_multiplier = 0.7
                    elif 10 <= hour <= 16:  # 낮 시간 - 증가 (쇼핑 등)
                        hour_multiplier = 1.3
                    elif 20 <= hour <= 23:  # 저녁 - 증가
                        hour_multiplier = 1.2
                    else:
                        hour_multiplier = 1.0
                else:
                    hour_multiplier = 1.0

                # 최종 충전 횟수 계산
                expected_count = int(base_count * day_multiplier * hour_multiplier)

                # 원본 데이터에서 해당 시간대 샘플링
                hour_data = self.charging_data[
                    self.charging_data['hour'].astype(int) == hour
                ].copy()

                if len(hour_data) > 0 and expected_count > 0:
                    # 복제 (부족하면 반복)
                    sampled = hour_data.sample(
                        n=expected_count,
                        replace=(expected_count > len(hour_data)),
                        random_state=42 + day * 100 + hour
                    ).copy()

                    # 시간 조정 (day 오프셋 추가)
                    base_time = day * 86400 + hour * 3600
                    sampled['time'] = base_time + np.random.uniform(0, 3600, len(sampled))
                    sampled['day'] = day
                    sampled['hour'] = hour
                    sampled['weekday'] = weekday
                    sampled['is_weekend'] = is_weekend

                    # 위치에 약간의 노이즈 추가 (현실성)
                    sampled['locationX'] += np.random.normal(0, 10, len(sampled))
                    sampled['locationY'] += np.random.normal(0, 10, len(sampled))

                    expanded_records.append(sampled)

        # 결합
        self.expanded_data = pd.concat(expanded_records, ignore_index=True)
        self.expanded_data = self.expanded_data.sort_values('time').reset_index(drop=True)

        print(f"✅ 확장 완료: {len(self.expanded_data)}개 충전 이벤트")
        print(f"   - 원본: {len(self.charging_data)}개 (1.27일)")
        print(f"   - 확장: {len(self.expanded_data)}개 (7일)")
        print(f"   - 비율: {len(self.expanded_data) / len(self.charging_data):.1f}배")

        return self.expanded_data

    def generate_ml_features(self):
        """ML 학습용 Feature 생성"""
        print("\n🤖 ML Feature 생성 중...")

        features = []

        # 시간대별 집계 (1시간 단위)
        for day in range(7):
            for hour in range(24):
                day_hour_data = self.expanded_data[
                    (self.expanded_data['day'] == day) &
                    (self.expanded_data['hour'] == hour)
                ]

                weekday = day % 7
                is_weekend = weekday >= 5

                feature = {
                    'timestamp': self.base_date + timedelta(days=day, hours=hour),
                    'day': day,
                    'hour': hour,
                    'weekday': weekday,
                    'is_weekend': int(is_weekend),
                    'weekday_name': ['월', '화', '수', '목', '금', '토', '일'][weekday],

                    # 충전 수요
                    'charging_count': len(day_hour_data),

                    # 시간대 특성
                    'is_morning_peak': int(7 <= hour <= 9),
                    'is_evening_peak': int(17 <= hour <= 19),
                    'is_night': int(22 <= hour or hour <= 6),
                    'is_business_hour': int(9 <= hour <= 18),

                    # 순환 인코딩 (시간의 주기성)
                    'hour_sin': np.sin(2 * np.pi * hour / 24),
                    'hour_cos': np.cos(2 * np.pi * hour / 24),
                    'day_sin': np.sin(2 * np.pi * day / 7),
                    'day_cos': np.cos(2 * np.pi * day / 7),
                }

                # 이동 평균 (3시간)
                window_data = self.expanded_data[
                    (self.expanded_data['day'] == day) &
                    (self.expanded_data['hour'] >= max(0, hour-1)) &
                    (self.expanded_data['hour'] <= min(23, hour+1))
                ]
                feature['charging_count_3h_avg'] = len(window_data) / 3

                features.append(feature)

        features_df = pd.DataFrame(features)

        print(f"✅ {len(features_df)}개 Feature 레코드 생성")
        print(f"   컬럼: {list(features_df.columns)}")

        return features_df

    def visualize_expansion(self, output_path='charging_7day_expansion.png'):
        """7일 확장 결과 시각화"""
        print("\n📊 시각화 생성 중...")

        fig, axes = plt.subplots(3, 1, figsize=(16, 12))

        # 1. 일별 충전 횟수
        daily_counts = self.expanded_data.groupby('day').size()
        weekday_names = ['월', '화', '수', '목', '금', '토', '일']
        colors = ['#3498db'] * 5 + ['#e74c3c'] * 2  # 평일 파랑, 주말 빨강

        axes[0].bar(range(7), daily_counts, color=colors, alpha=0.7)
        axes[0].set_xticks(range(7))
        axes[0].set_xticklabels(weekday_names)
        axes[0].set_ylabel('충전 횟수', fontsize=12)
        axes[0].set_title('일별 충전 수요 (평일 vs 주말)', fontsize=14, fontweight='bold')
        axes[0].grid(axis='y', alpha=0.3)

        for i, count in enumerate(daily_counts):
            axes[0].text(i, count + 5, str(count), ha='center', va='bottom', fontweight='bold')

        # 2. 시간대별 히트맵 (요일 × 시간)
        pivot_data = self.expanded_data.groupby(['day', 'hour']).size().unstack(fill_value=0)

        sns.heatmap(pivot_data, ax=axes[1], cmap='YlOrRd', cbar_kws={'label': '충전 횟수'})
        axes[1].set_xlabel('시간 (hour)', fontsize=12)
        axes[1].set_ylabel('요일', fontsize=12)
        axes[1].set_yticklabels(weekday_names, rotation=0)
        axes[1].set_title('시간대별 충전 수요 히트맵', fontsize=14, fontweight='bold')

        # 3. 평일 vs 주말 시간대별 패턴 비교
        weekday_pattern = self.expanded_data[~self.expanded_data['is_weekend']].groupby('hour').size()
        weekend_pattern = self.expanded_data[self.expanded_data['is_weekend']].groupby('hour').size()

        hours = range(24)
        axes[2].plot(hours, [weekday_pattern.get(h, 0) for h in hours],
                     marker='o', label='평일 (월-금)', linewidth=2, color='#3498db')
        axes[2].plot(hours, [weekend_pattern.get(h, 0) for h in hours],
                     marker='s', label='주말 (토-일)', linewidth=2, color='#e74c3c')
        axes[2].set_xlabel('시간 (hour)', fontsize=12)
        axes[2].set_ylabel('충전 횟수', fontsize=12)
        axes[2].set_title('평일 vs 주말 시간대별 충전 패턴', fontsize=14, fontweight='bold')
        axes[2].legend(fontsize=11)
        axes[2].grid(alpha=0.3)
        axes[2].set_xticks(range(0, 24, 2))

        # 피크 시간대 강조
        axes[2].axvspan(7, 9, alpha=0.2, color='yellow', label='출근 시간대')
        axes[2].axvspan(17, 19, alpha=0.2, color='orange', label='퇴근 시간대')

        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✅ 시각화 저장: {output_path}")

        return fig

    def save_data(self, expanded_csv='charging_7days_expanded.csv',
                  features_csv='charging_ml_features_7days.csv'):
        """확장된 데이터 저장"""
        print("\n💾 데이터 저장 중...")

        # 확장된 충전 데이터
        self.expanded_data.to_csv(expanded_csv, index=False)
        print(f"✅ 확장 데이터 저장: {expanded_csv}")

        # ML Feature
        features = self.generate_ml_features()
        features.to_csv(features_csv, index=False)
        print(f"✅ ML Feature 저장: {features_csv}")

        return features

    def print_statistics(self):
        """통계 요약 출력"""
        print("\n" + "="*80)
        print("📊 7일 확장 데이터 통계 요약")
        print("="*80)

        # 일별 통계
        daily_stats = self.expanded_data.groupby('day').agg({
            'time': 'count',
            'vehicle': 'nunique'
        }).rename(columns={'time': 'charging_count', 'vehicle': 'unique_vehicles'})

        weekday_names = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
        daily_stats['weekday'] = weekday_names

        print("\n일별 충전 통계:")
        print(daily_stats.to_string())

        # 평일 vs 주말
        weekday_total = self.expanded_data[~self.expanded_data['is_weekend']]['time'].count()
        weekend_total = self.expanded_data[self.expanded_data['is_weekend']]['time'].count()

        print(f"\n평일 총 충전: {weekday_total}회 (평균 {weekday_total/5:.1f}회/일)")
        print(f"주말 총 충전: {weekend_total}회 (평균 {weekend_total/2:.1f}회/일)")
        print(f"주말 증가율: {(weekend_total/2) / (weekday_total/5) - 1:.1%}")

        # 시간대별 피크
        hourly_avg = self.expanded_data.groupby('hour').size() / 7
        peak_hour = hourly_avg.idxmax()
        print(f"\n피크 시간대: {int(peak_hour)}시 (평균 {hourly_avg[peak_hour]:.1f}회)")

        print("="*80)

def main():
    """메인 실행 함수"""

    # 이벤트 파일 찾기
    base_path = Path('.')
    events_files = list(base_path.glob('output/sf-light/**/ITERS/it.*/5.events.csv'))
    if not events_files:
        events_files = list(base_path.glob('output/sf-light/**/ITERS/it.*/0.events.csv'))

    if not events_files:
        print("❌ 이벤트 파일을 찾을 수 없습니다.")
        print("   경로를 확인하거나 직접 지정하세요:")
        print("   expander = ChargingDataExpander('output/.../5.events.csv')")
        return

    events_file = events_files[0]
    print(f"📁 이벤트 파일: {events_file}\n")

    # 확장 실행
    expander = ChargingDataExpander(events_file)
    expander.load_data()
    expander.analyze_hourly_pattern()
    expander.expand_to_7days(weekend_multiplier=1.15)

    # 시각화 및 저장
    expander.visualize_expansion()
    features = expander.save_data()
    expander.print_statistics()

    print("\n" + "="*80)
    print("✅ 7일 확장 완료!")
    print("="*80)
    print("\n생성된 파일:")
    print("  1. charging_7days_expanded.csv - 7일치 충전 이벤트 데이터")
    print("  2. charging_ml_features_7days.csv - ML 학습용 Feature")
    print("  3. charging_7day_expansion.png - 시각화 결과")
    print("\n다음 단계:")
    print("  - ML 모델 학습 (시간대별 충전 수요 예측)")
    print("  - Feature Engineering 추가")
    print("  - 모델 평가 및 최적화")

if __name__ == '__main__':
    main()