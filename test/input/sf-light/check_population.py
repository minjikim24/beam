# Population 파일 내 활동 시간 범위 확인

import xml.etree.ElementTree as ET
import gzip

with gzip.open('test/input/sf-light/sample/1k/population.xml.gz', 'rt') as f:
    root = ET.parse(f).getroot()

times = []
for person in root.findall('.//person')[:10]:  # 첫 10명 샘플
    for plan in person.findall('plan'):
        for activity in plan.findall('activity'):
            end_time = activity.get('end_time')
            if end_time and end_time != '24:00:00':
                times.append(end_time)

print('활동 종료 시간 샘플:', times[:20])
print('최대 활동 시간:', max(times) if times else 'None')
