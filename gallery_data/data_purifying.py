import pandas as pd
import json
# [수정] pyproj 라이브러리는 더 이상 필요 없으므로 주석 처리하거나 제거 가능
# from pyproj import Transformer, CRS

# CSV 파일 경로를 지정합니다.
# 이 파일을 실행하는 파이썬 스크립트와 같은 폴더에 CSV 파일이 있다면 파일 이름만 적으면 됩니다.
file_path = './gallery_data/전국박물관미술관정보표준데이터.csv' # 여기에 실제 CSV 파일 이름을 입력해주세요.

try:
    df = pd.read_csv(file_path, encoding='utf-8')
except UnicodeDecodeError:
    print(f"'{file_path}' 파일을 utf-8 인코딩으로 읽는 데 실패했습니다. euc-kr 인코딩으로 다시 시도합니다.")
    df = pd.read_csv(file_path, encoding='euc-kr')
except FileNotFoundError:
    print(f"오류: '{file_path}' 파일을 찾을 수 없습니다. 파일 경로가 올바른지 확인해주세요.")
    exit()

print("--- 원본 데이터 로드 완료 ---")
print(f"총 {len(df)}개의 데이터가 로드되었습니다.")

# [추가] CSV 파일의 실제 컬럼명들을 출력하여 확인합니다.
print("\n--- CSV 파일의 실제 컬럼명 (이것을 보고 column_mapping을 수정하세요!) ---")
print(df.columns.tolist()) # 리스트 형태로 출력하여 보기 쉽게 합니다.
print("----------------------------------------------------------------------")

# 1. 필요한 컬럼만 선택하고 웹 페이지에 사용할 이름으로 표준화합니다.
# [수정] 새로운 컬럼명에 맞춰 column_mapping 업데이트 및 관람료/시간/휴관 정보 추가
column_mapping = {
    '시설명': 'name',
    '소재지도로명주소': 'address',
    '운영기관전화번호': 'phone',
    '위도': 'latitude',  # 새로운 데이터셋은 위도, 경도를 직접 제공
    '경도': 'longitude', # 새로운 데이터셋은 위도, 경도롤 직접 제공
    '박물관미술관구분': 'type', # '박물관미술관종류명' -> '박물관미술관구분'
    '영업상태명': 'status',
    '어른관람료': 'adult_admission_fee',       # [추가]
    '청소년관람료': 'youth_admission_fee',     # [추가]
    '어린이관람료': 'child_admission_fee',     # [추가]
    '관람료기타정보': 'other_admission_info', # [추가]
    '평일관람시작시각': 'weekday_open_time',   # [추가]
    '평일관람종료시각': 'weekday_close_time',  # [추가]
    '공휴일관람시작시각': 'holiday_open_time', # [추가]
    '공휴일관람종료시각': 'holiday_close_time',# [추가]
    '휴관정보': 'closing_info',              # [추가]
    '박물관미술관소개': 'description',         # [추가] 박물관 소개 정보
    '운영홈페이지': 'website'                 # [추가] 웹사이트 정보
}

selected_columns = {k: v for k, v in column_mapping.items() if k in df.columns}
df_processed = df[list(selected_columns.keys())].rename(columns=selected_columns)

print("\n--- 선택된 컬럼 및 표준화된 컬럼명 미리보기 ---")
print(df_processed.head())
print("\n--- 선택된 컬럼 정보 ---")
df_processed.info()

# 2. '영업상태'가 '영업/정상'인 데이터만 필터링합니다.
if 'status' in df_processed.columns:
    initial_rows = len(df_processed)
    df_processed = df_processed[df_processed['status'] == '영업/정상'].copy()
    print(f"\n'영업상태'가 '영업/정상'인 데이터만 필터링 후 {len(df_processed)}개 남았습니다. ({initial_rows - len(df_processed)}개 제거)")
else:
    print("\n'status' 컬럼이 존재하지 않아 영업 상태 필터링을 건너뜁니다.")

# 3. 필수 정보 (이름, 주소, 좌표) 결측치 처리
# [수정] critical_columns_for_web에 위도, 경도 직접 사용
critical_columns_for_web = ['name', 'address', 'latitude', 'longitude']
existing_critical_columns = [col for col in critical_columns_for_web if col in df_processed.columns]

if existing_critical_columns:
    initial_rows_after_status_filter = len(df_processed)
    df_processed.dropna(subset=existing_critical_columns, inplace=True)
    print(f"필수 컬럼({', '.join(existing_critical_columns)}) 결측치 제거 후 {len(df_processed)}개 남았습니다. ({initial_rows_after_status_filter - len(df_processed)}개 제거)")
else:
    print("\n필수 컬럼이 존재하지 않아 결측치 제거를 건너뜠습니다.")

# [주석 처리] 4. 위경도 컬럼 숫자형으로 변환 (EPSG:5174 좌표) - 새로운 데이터셋에서는 필요 없음
# for coord_col in ['x_coord_epsg5174', 'y_coord_epsg5174']:
#     if coord_col in df_processed.columns:
#         df_processed[coord_col] = pd.to_numeric(df_processed[coord_col], errors='coerce')
#         df_processed.dropna(subset=[coord_col], inplace=True)
#         print(f"'{coord_col}' 컬럼을 숫자형으로 변환하고 NaN 제거 완료. 현재 행 개수: {len(df_processed)}")

# [추가] 4. 위도, 경도 컬럼 숫자형으로 변환 (새로운 데이터셋에 맞춰 추가)
for coord_col in ['latitude', 'longitude']:
    if coord_col in df_processed.columns:
        df_processed[coord_col] = pd.to_numeric(df_processed[coord_col], errors='coerce')
        df_processed.dropna(subset=[coord_col], inplace=True)
        print(f"'{coord_col}' 컬럼을 숫자형으로 변환하고 NaN 제거 완료. 현재 행 개수: {len(df_processed)}")


# [주석 처리] 5. EPSG:5174 좌표를 WGS84 (위도, 경도)로 변환 - 새로운 데이터셋에서는 필요 없음
# try:
#     transformer = Transformer.from_crs(CRS("EPSG:5174"), CRS("EPSG:4326"), always_xy=True)
#     valid_coords_df = df_processed.dropna(subset=['x_coord_epsg5174', 'y_coord_epsg5174'])
    
#     lon_lat_coords = [transformer.transform(x, y) for x, y in zip(valid_coords_df['x_coord_epsg5174'], valid_coords_df['y_coord_epsg5174'])]
    
#     df_processed['longitude'] = pd.Series([coord[0] for coord in lon_lat_coords], index=valid_coords_df.index)
#     df_processed['latitude'] = pd.Series([coord[1] for coord in lon_lat_coords], index=valid_coords_df.index)

#     df_processed.dropna(subset=['latitude', 'longitude'], inplace=True)
#     print(f"\nEPSG:5174 -> WGS84 좌표 변환 완료. 현재 행 개수: {len(df_processed)}")

# except ImportError:
#     print("\n경고: 'pyproj' 라이브러리가 설치되어 있지 않습니다. 좌표 변환을 건너뜠습니다.")
#     print("pip install pyproj 명령어로 설치 후 다시 시도해주세요.")
#     df_processed['latitude'] = None
#     df_processed['longitude'] = None
# except Exception as e:
#     print(f"\n좌표 변환 중 오류 발생: {e}. 좌표 변환을 건너뜠습니다.")
#     df_processed['latitude'] = None
#     df_processed['longitude'] = None


# 6. 기타 텍스트 컬럼 결측치 빈 문자열로 채우기
# [수정] 새로운 관람료, 시간, 휴관, 웹사이트, 소개 컬럼 추가
for col in [
    'phone', 'type', 'adult_admission_fee', 'youth_admission_fee', 
    'child_admission_fee', 'other_admission_info', 'weekday_open_time', 
    'weekday_close_time', 'holiday_open_time', 'holiday_close_time', 
    'closing_info', 'description', 'website'
]:
    if col in df_processed.columns:
        df_processed[col] = df_processed[col].fillna('')

# 7. 텍스트 데이터 정제 (불필요한 공백 제거 등)
def clean_text(text):
    if isinstance(text, str):
        return text.strip()
    return text

# [수정] 새로운 관람료, 시간, 휴관, 웹사이트, 소개 컬럼 추가
for col in [
    'name', 'address', 'phone', 'type', 'adult_admission_fee', 
    'youth_admission_fee', 'child_admission_fee', 'other_admission_info', 
    'weekday_open_time', 'weekday_close_time', 'holiday_open_time', 
    'holiday_close_time', 'closing_info', 'description', 'website'
]:
    if col in df_processed.columns:
        df_processed[col] = df_processed[col].apply(clean_text)

# 8. 중복 데이터 제거 (선택 사항: 'name'과 'address' 기준으로 중복 제거)
if 'name' in df_processed.columns and 'address' in df_processed.columns:
    initial_rows_before_deduplication = len(df_processed)
    df_processed.drop_duplicates(subset=['name', 'address'], inplace=True)
    print(f"\n이름과 주소 기준 중복 제거 후 {len(df_processed)}개 남았습니다. ({initial_rows_before_deduplication - len(df_processed)}개 제거)")


# 9. 최종 데이터 확인
print("\n--- 최종 정제된 데이터 미리보기 ---")
print(df_processed.head())
print("\n--- 최종 정제된 데이터 정보 ---")
df_processed.info()
print("\n--- 최종 정제된 데이터 컬럼별 결측치 확인 ---")
print(df_processed.isnull().sum())

# 10. 웹 페이지에서 사용하기 쉽도록 JSON 형태로 저장
# [수정] final_columns에 새로운 관람료, 시간, 휴관, 웹사이트, 소개 컬럼 추가
final_columns = [
    'name', 'address', 'phone', 'type', 'latitude', 'longitude', 'status',
    'adult_admission_fee', 'youth_admission_fee', 'child_admission_fee', 
    'other_admission_info', 'weekday_open_time', 'weekday_close_time', 
    'holiday_open_time', 'holiday_close_time', 'closing_info',
    'description', 'website'
]
final_df = df_processed[[col for col in final_columns if col in df_processed.columns]]

output_json_path = './gallery_data/cleaned_museum_data.json'
final_df.to_json(output_json_path, orient='records', force_ascii=False, indent=4)

print(f"\n데이터 정제가 완료되었습니다. '{output_json_path}' 파일로 저장되었습니다.")
