# D:\\project3_test\\\\llm_cores\\\\negative_prompts.py

# [추가 부분] 미리 정의된 부정 프롬프트 카테고리 맵
# 각 키는 카테고리 이름이고, 값은 해당 카테고리에 적용될 부정 프롬프트 문자열입니다.
NEGATIVE_PROMPT_MAP = {
    "bad_quality": "low quality, bad quality, worst quality, jpeg artifacts, blurry, noisy, grainy, deformed, distorted",
    "bad_anatomy": "bad anatomy, extra limbs, missing limbs, malformed, mutated, ugly, disfigured, bad hands, extra fingers, fused fingers",
    "text_watermark": "text, watermark, signature, logo, writing, words, numbers, brand",
    "nsfw": "nude, naked, explicit, sexual, porn, gore, violence, blood, disgusting",
    "person": "person, people, human, man, woman, boy, girl, child, face, body, hands, feet, multiple people",
    "animal": "animal, pet, dog, cat, bird, fish, wild animal, multiple animals",
    "plant": "plant, flower, tree, bush, leaf, grass, multiple plants",
    "landscape": "landscape, outdoor, nature, mountain, sky, water, city, building, urban, rural",
    "abstract": "abstract, surreal, non-representational, conceptual, blurry background",
    "2d_feel": "flat, cartoon, illustration, drawing, sketch, anime, comic, graphic",
    "3d_feel": "2d, painting, art, abstract, hand-drawn, unrealistic",
    "bad_resolution": "low resolution, pixelated, blurry, jagged edges",
    "too_many_objects": "too many, multiple, cluttered, crowded, chaotic, busy",
    "too_few_objects": "too few, sparse, empty, lonely",
    # [추가 부분 시작] 새로운 부정 프롬프트 카테고리 (장르별 상충 요소)
    "unwanted_realism": "photorealistic, hyperrealistic, realistic, naturalistic, real photo, 3D, CGI, render, detailed skin texture, pores, wrinkles, realistic hair", # 비현실적/스타일화된 그림에서 사실주의를 피할 때
    "unwanted_stylization": "cartoon, anime, comic, illustration, painting, drawing, abstract, stylized, fantastical, whimsical, exaggerated features, flat colors, simplified forms, brushstrokes, watercolor bleed, pixelated", # 사실적인 그림에서 스타일화를 피할 때
    "unnatural_colors": "dull colors, desaturated, monochrome, grayscale, unnatural color palette, oversaturated, undersaturated, muted colors",
    "poor_composition": "awkward composition, bad composition, cluttered, unbalanced, distracting elements, poorly framed, chaotic layout",
    "art_medium_artifacts": "brushstrokes, paint smears, canvas texture, paper texture, pencil marks, crayon marks, grainy film, traditional medium artifacts", # 디지털 아트 등에서 특정 매체 흔적을 피할 때
    "lack_of_detail": "low detail, simple, plain, generic, undetailed", # 특정 장르에서 디테일 부족을 피할 때
    "excessive_detail": "overly detailed, busy, cluttered, too much detail", # 미니멀리즘 등에서 과도한 디테일을 피할 때
    "static_pose": "static pose, stiff, unnatural pose, rigid", # 역동적인 포즈를 원할 때
    "unwanted_abstraction": "abstract, non-representational, conceptual, distorted, surreal, dreamlike", # 구체적인 대상을 원할 때
    # [추가 부분 시작] 화가 스타일과 상충되는 부정 프롬프트
    "anti_impressionist": "sharp lines, crisp details, solid forms, static composition, dark shadows", # 인상주의와 상충
    "anti_cubist": "smooth forms, natural perspective, realistic proportions, continuous lines", # 입체주의와 상충
    "anti_surrealist": "logical, realistic, rational, mundane, everyday objects in normal context", # 초현실주의와 상충
    "anti_pop_art": "subtle colors, painterly, traditional art, complex textures, fine art", # 팝 아트와 상충
    "anti_minimalist": "complex, busy, decorative, elaborate, highly detailed, cluttered", # 미니멀리즘과 상충
    "anti_digital_art": "hand-drawn, traditional medium, brushstrokes, paper texture, canvas texture", # 디지털 아트와 상충
    # [추가 부분 시작] 마블 및 디즈니 스타일과 상충되는 부정 프롬프트
    "anti_marvel_style": "soft shading, pastel colors, realistic proportions, subtle emotions, flat colors, watercolor, painterly, children's book illustration", # 마블과 상충
    # [수정] Disney 스타일과 상충되는 부정 프롬프트 디테일 강화
    "anti_disney_style": "gritty, dark, violent, horror, disturbing, hyperrealistic, adult themes, complex shading, rough lines, photorealistic, overly detailed textures, **sharp angles, realistic anatomy, muted colors, abstract forms, harsh lighting, gritty textures, dramatic shadows, non-expressive faces, stiff poses, complex narratives, mature themes, disturbing imagery, pixelated, low resolution, traditional painting, oil painting, watercolor**",
    # [추가 부분 시작] 동양화 스타일과 상충되는 부정 프롬프트
    "anti_ink_wash": "vibrant colors, excessive detail, photorealistic, Western art style, complex composition, harsh lines, strong contrast", # 수묵화와 상충
    "anti_color_painting": "monochrome, ink wash, minimalist, muted colors, sketchy, rough lines, abstract", # 채색화와 상충
    "anti_ukiyo_e": "realistic, 3D, complex shading, subtle colors, Western art style, modern digital art, soft lines, detailed textures", # 우키요에와 상충
    "anti_nihonga": "bold outlines, flat colors, Western art style, digital art, cartoonish, rough textures, pop art", # 일본화와 상충
    "anti_gongbi": "freehand, expressive, spontaneous, ink wash, minimalist, rough lines, Western art style, abstract", # 공필화와 상충
    "anti_xieyi": "meticulous detail, fine lines, vibrant colors, precise, realistic, Western art style, detailed texture", # 사의와 상충
    # [추가 부분 시작] 동양화 화가 스타일과 상충되는 부정 프롬프트
    # 한국화 화가
    "anti_jeong_seon": "abstract, unrealistic, vibrant colors, detailed figures, Western art style", # 정선
    "anti_kim_jeong_hui": "realistic, detailed, vibrant colors, complex composition, Western art style", # 김정희
    "anti_jang_seung_eop": "simple, static, monochrome, abstract, Western art style", # 장승업
    "anti_yi_am": "abstract, human figures, complex, blurred, non-animal subjects", # 이암
    "anti_byeon_sang_byeok": "abstract, human figures, complex, blurred, non-animal subjects", # 변상벽
    "anti_shin_saimdang": "rough, abstract, large scale, human figures, dark colors", # 신사임당
    "anti_kim_hong_do": "static, idealized, abstract, Western art style, complex composition", # 김홍도
    "anti_kang_se_hwang": "realistic, detailed, vibrant colors, complex composition, Western art style", # 강세황
    "anti_yun_du_seo": "idealized, abstract, non-human, Western art style, complex composition", # 윤두서
    # 중국화 화가
    "anti_wang_wei": "vibrant colors, complex, detailed, realistic, Western art style", # 왕유
    "anti_dong_yuan": "sharp lines, clear forms, vibrant colors, Western art style, urban scenes", # 동원
    "anti_juran": "sharp lines, clear forms, vibrant colors, Western art style, urban scenes", # 거연
    "anti_ma_yuan": "full composition, soft brushwork, abstract, Western art style", # 마원
    "anti_xia_gui": "full composition, soft brushwork, abstract, Western art style", # 하규
    "anti_huang_gongwang": "vibrant colors, smooth, flat, Western art style, detailed figures", # 황공망
    "anti_ni_zan": "dense, cluttered, vibrant colors, realistic, Western art style", # 예찬
    "anti_wang_meng": "sparse, simple, flat, Western art style, abstract", # 왕몽
    "anti_wu_zhen": "complex, detailed, vibrant colors, Western art style, non-bamboo subjects", # 오진
    "anti_shi_tao": "rigid, conventional, academic, realistic, Western art style", # 석도
    "anti_bada_shanren": "complex, vibrant colors, realistic, Western art style, cheerful", # 팔대산인
    "anti_qiu_ying": "loose brushwork, abstract, monochrome, Western art style, simple scenes", # 구영
    "anti_emperor_huizong": "rough, abstract, human figures, dark colors, Western art style", # 송 휘종
    "anti_liang_kai": "meticulous detail, vibrant colors, complex composition, Western art style", # 양찬
    "anti_muqi_fachang": "meticulous detail, vibrant colors, complex composition, Western art style", # 목계
    # 일본화 화가
    "anti_katsushika_hokusai": "soft colors, subtle details, realistic, Western art style, static composition", # 가쓰시카 호쿠사이
    "anti_utagawa_hiroshige": "sharp details, vibrant colors, realistic, Western art style, static composition", # 우타가와 히로시게
    "anti_toshusai_sharaku": "realistic, subtle expressions, full body, Western art style", # 도슈사이 샤라쿠
    "anti_kitagawa_utamaro": "rough, abstract, male figures, Western art style, complex composition", # 기타가와 우타마로
    "anti_yokoyama_taikan": "sharp lines, vibrant colors, Western art style, realistic, detailed", # 요코야마 다이칸
    "anti_hishida_shunso": "bold lines, harsh colors, Western art style, realistic, detailed", # 히시다 슌소
    "anti_sesshu_toyo": "vibrant colors, excessive detail, realistic, Western art style, complex composition", # 셋슈 도요
    "anti_sen_no_rikyu": "complex, ornate, vibrant colors, Western art style, detailed", # 센노 리큐
    "anti_kanaoka_takanobu": "monochrome, abstract, Western art style, simple composition", # 가나오카 다카노부
    "anti_kano_eitoku": "subtle, minimalist, Western art style, small scale, simple", # 가노 에이토쿠
    "anti_kano_tanyu": "bold, dynamic, vibrant colors, Western art style, large scale", # 가노 단유
    "anti_ogata_korin": "subtle, realistic, Western art style, complex composition, muted colors", # 오가타 고린
    "tawaraya_sotatsu_style": "subtle, realistic, Western art style, complex composition, muted colors", # 다와라야 소타쓰
    # [추가 부분 끝]

    # [추가 부분 시작] 이미지 원본 유지 방지 관련 부정 프롬프트
    "distorted_pose": "distorted pose, unnatural pose, mutated limbs, twisted posture, changed body language, incorrect stance, altered pose",
    "color_shift": "color shift, desaturated colors, oversaturated colors, monochrome, grayscale, altered color palette, unnatural colors, vibrant colors (if undesired), muted colors (if undesired)",
    "distorted_form": "distorted form, warped shape, altered silhouette, changed outline, unrecognizable object, blurred form, melted, deformed",
    # [새로 추가된 부분] 얼굴 특징 및 인종/민족적 특징 변경 방지 부정 프롬프트
    "distorted_facial_features": "distorted face, malformed eyes, crooked nose, misshapen mouth, asymmetrical face, changed expression, wrong skin tone, altered hair, unwanted facial hair, blurred face, ugly face, deformed face",
    "unwanted_ethnic_shift": "western facial features, caucasian features, african features, middle eastern features, indian features, european features, different ethnicity, altered racial characteristics, changed cultural appearance, non-East Asian features, non-Korean features, non-Japanese features, non-Chinese features",
    "distorted_body_shape": "distorted body, warped body shape, altered physique, inconsistent body proportions, deformed body contours",
    # [새로 추가된 부분] 3D 및 입체감 부족 방지 부정 프롬프트
    "lack_of_realism": "unrealistic, artificial, fake, cartoonish, painterly (if realism desired), stylized (if realism desired), simplified, abstract, flat rendering, poor texture, blurry, unsharp, low fidelity, plastic look, fake look, CGI look (if undesired)",
    "lack_of_3d_depth": "flat, 2D, no depth, paper-thin, lacking volume, shallow perspective, poor dimensionality, weak shadows, no sense of mass, un-sculptural, silhouette-like",
    "unwanted_surrealism_distortion": "distorted reality, illogical composition, abstract elements (if realism desired), dreamlike blur, non-tangible forms, impossible physics (if realism desired)"
    # [추가 부분 끝]
}
