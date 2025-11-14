#!/usr/bin/env python3
"""
BEAM 차량 파일에서 EV 비율 조정 스크립트
Usage: python convert_to_ev.py --ratio 0.5
"""

import pandas as pd
import gzip
import shutil
import random
import argparse
from pathlib import Path

def convert_fleet_to_ev(
    input_path: str = 'test/input/sf-light/sample/1k/vehicles.csv.gz',
    output_path: str = None,
    ev_ratio: float = 0.5,
    ev_type_id: str = 'BEV',  # 또는 '2'로 지정 가능
    seed: int = 42
):
    """
    차량 플릿의 일부를 EV로 변환
    
    Args:
        input_path: 입력 차량 파일 경로 (CSV 또는 CSV.GZ)
        output_path: 출력 파일 경로 (None이면 자동 생성)
        ev_ratio: EV 비율 (0.0 ~ 1.0)
        ev_type_id: EV 차량 타입 ID
        seed: 랜덤 시드 (재현성 확보)
    """
    
    # 1. 출력 파일 경로 설정
    if output_path is None:
        input_file = Path(input_path)
        ratio_str = str(int(ev_ratio * 100))
        output_path = str(input_file.parent / f'vehicles-{ratio_str}pct-ev.csv.gz')
    
    print(f"📂 입력 파일: {input_path}")
    print(f"📂 출력 파일: {output_path}")
    
    # 2. 파일 로드
    if input_path.endswith('.gz'):
        vehicles = pd.read_csv(input_path, compression='gzip')
    else:
        vehicles = pd.read_csv(input_path)
    
    print(f"\n📊 총 차량 수: {len(vehicles)}")
    print(f"🎯 목표 EV 비율: {ev_ratio * 100:.1f}%")
    
    # 3. 현재 차량 타입 분포
    print(f"\n🚗 변환 전 차량 타입 분포:")
    type_counts_before = vehicles['vehicleTypeId'].value_counts()
    print(type_counts_before)
    
    # 4. EV로 변환할 차량 랜덤 선택
    random.seed(seed)
    num_evs = int(len(vehicles) * ev_ratio)
    ev_indices = random.sample(range(len(vehicles)), num_evs)
    
    # 5. vehicleTypeId 변경
    vehicles_copy = vehicles.copy()
    vehicles_copy.loc[ev_indices, 'vehicleTypeId'] = ev_type_id
    
    # 6. 통계 출력
    print(f"\n🔋 변환 후 차량 타입 분포:")
    type_counts_after = vehicles_copy['vehicleTypeId'].value_counts()
    print(type_counts_after)
    
    ev_count = type_counts_after.get(ev_type_id, 0)
    actual_ratio = ev_count / len(vehicles) * 100
    print(f"\n✅ 실제 EV 비율: {actual_ratio:.2f}% ({ev_count}/{len(vehicles)} 대)")
    
    # 7. 파일 저장
    if output_path.endswith('.gz'):
        # 임시 CSV 생성 후 압축
        temp_csv = output_path.replace('.gz', '')
        vehicles_copy.to_csv(temp_csv, index=False)
        
        with open(temp_csv, 'rb') as f_in:
            with gzip.open(output_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # 임시 파일 삭제
        Path(temp_csv).unlink()
    else:
        vehicles_copy.to_csv(output_path, index=False)
    
    print(f"\n💾 저장 완료: {output_path}")
    
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='BEAM 차량 파일에서 EV 비율 조정'
    )
    parser.add_argument(
        '--input', '-i',
        default='test/input/sf-light/sample/1k/vehicles.csv.gz',
        help='입력 차량 파일 경로'
    )
    parser.add_argument(
        '--output', '-o',
        default=None,
        help='출력 파일 경로 (지정하지 않으면 자동 생성)'
    )
    parser.add_argument(
        '--ratio', '-r',
        type=float,
        default=0.5,
        help='EV 비율 (0.0~1.0, 기본값: 0.5 = 50%%)'
    )
    parser.add_argument(
        '--ev-type-id',
        default='BEV',
        help='EV 차량 타입 ID (기본값: BEV)'
    )
    parser.add_argument(
        '--seed', '-s',
        type=int,
        default=42,
        help='랜덤 시드 (재현성, 기본값: 42)'
    )
    
    args = parser.parse_args()
    
    # 비율 검증
    if not 0.0 <= args.ratio <= 1.0:
        parser.error("--ratio는 0.0과 1.0 사이여야 합니다")
    
    convert_fleet_to_ev(
        input_path=args.input,
        output_path=args.output,
        ev_ratio=args.ratio,
        ev_type_id=args.ev_type_id,
        seed=args.seed
    )


if __name__ == '__main__':
    main()
