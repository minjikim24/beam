"""
BEAM Population 파일 시간 범위 분석 스크립트
- 모든 population 파일의 최대 시간 범위 확인
- 7일 시뮬레이션 가능 여부 판단
"""

import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

def check_population_time_range(filepath):
    """Population 파일의 시간 범위 확인"""
    try:
        with gzip.open(filepath, 'rt') as f:
            tree = ET.parse(f)
            root = tree.getroot()
            
            max_time = 0
            activity_count = 0
            person_count = 0
            
            for person in root.findall('.//person'):
                person_count += 1
                for plan in person.findall('.//plan'):
                    for activity in plan.findall('.//activity'):
                        activity_count += 1
                        end_time = activity.get('end_time')
                        if end_time:
                            # HH:MM:SS 형식을 초로 변환
                            h, m, s = map(int, end_time.split(':'))
                            seconds = h * 3600 + m * 60 + s
                            max_time = max(max_time, seconds)
            
            days = max_time / 86400
            return {
                'file': filepath.name,
                'path': str(filepath.relative_to(Path('test/input/sf-light'))),
                'size_mb': filepath.stat().st_size / (1024 * 1024),
                'max_time_seconds': max_time,
                'max_time_hours': max_time / 3600,
                'max_time_days': days,
                'person_count': person_count,
                'activity_count': activity_count,
                'suitable_7days': days >= 7
            }
    except Exception as e:
        return {
            'file': filepath.name, 
            'path': str(filepath),
            'error': str(e)
        }

def main():
    # 모든 population 파일 찾기
    base_path = Path('test/input/sf-light/sample')
    pop_files = list(base_path.rglob('population*.xml.gz'))
    
    print("=" * 100)
    print("📊 BEAM Population 파일 시간 범위 분석")
    print("=" * 100)
    print(f"\n총 {len(pop_files)}개 파일 발견\n")
    
    if not pop_files:
        print("❌ Population 파일을 찾을 수 없습니다.")
        print(f"   검색 경로: {base_path.absolute()}")
        return
    
    print(f"{'경로':<35} {'크기(MB)':<10} {'인원':<8} {'활동수':<10} {'최대시간(h)':<15} {'일수':<10} {'7일가능':<10}")
    print("-" * 100)
    
    results = []
    for pop_file in sorted(pop_files):
        result = check_population_time_range(pop_file)
        results.append(result)
        
        if 'error' in result:
            print(f"{result['path']:<35} ERROR: {result['error']}")
        else:
            suitable = "✅" if result['suitable_7days'] else "❌"
            print(f"{result['path']:<35} "
                  f"{result['size_mb']:<10.2f} "
                  f"{result['person_count']:<8} "
                  f"{result['activity_count']:<10} "
                  f"{result['max_time_hours']:<15.2f} "
                  f"{result['max_time_days']:<10.2f} "
                  f"{suitable:<10}")
    
    # 7일 이상 커버하는 파일 찾기
    print("\n" + "=" * 100)
    print("🎯 7일 시뮬레이션 가능한 파일:")
    print("=" * 100)
    
    suitable_files = [r for r in results if 'error' not in r and r['suitable_7days']]
    if suitable_files:
        for f in suitable_files:
            print(f"\n  ✅ {f['path']}")
            print(f"     - 크기: {f['size_mb']:.2f} MB")
            print(f"     - 인원: {f['person_count']:,}명")
            print(f"     - 커버 범위: {f['max_time_days']:.2f}일 ({f['max_time_hours']:.2f}시간)")
    else:
        print("\n  ⚠️ 7일 이상 커버하는 파일이 없습니다.\n")
        
        # 가장 긴 파일 찾기
        valid_results = [r for r in results if 'error' not in r]
        if valid_results:
            longest = max(valid_results, key=lambda x: x['max_time_days'])
            print(f"  📌 가장 긴 시간 범위를 가진 파일:")
            print(f"     {longest['path']}")
            print(f"     - 커버 범위: {longest['max_time_days']:.2f}일 ({longest['max_time_hours']:.2f}시간)")
        
        print("\n  💡 해결 방안:")
        print("     1. 더 큰 샘플 사용 (10k, 25k 등)")
        print("     2. BEAM 설정에서 일일 계획 반복 활성화")
        print("     3. 다른 시나리오 파일 확인")

if __name__ == '__main__':
    main()