"""
Paint Essential - Internationalization (i18n) Engine
LJack Protocol: Decoupled translation dictionary and dynamic runtime retranslation.
Provides clean, functional, non-bloated Korean and English text mappings.
"""
from typing import Dict, Optional


class I18N:
    _current_language: str = "ko"

    TRANSLATIONS: Dict[str, Dict[str, str]] = {
        # App & Window
        "app_title": {
            "ko": "Paint Essential (페인트 에센셜) - LJack Edition",
            "en": "Paint Essential - LJack Edition",
        },
        "untitled": {
            "ko": "제목 없음",
            "en": "Untitled",
        },

        # Ribbon Toolbar File Actions
        "act_new": {
            "ko": "새로 만들기",
            "en": "New",
        },
        "act_new_tip": {
            "ko": "새 캔버스 생성 (Ctrl+N)",
            "en": "Create new canvas (Ctrl+N)",
        },
        "act_open": {
            "ko": "열기",
            "en": "Open",
        },
        "act_open_tip": {
            "ko": "이미지 파일 열기 (Ctrl+O)",
            "en": "Open image file (Ctrl+O)",
        },
        "act_save": {
            "ko": "저장",
            "en": "Save",
        },
        "act_save_tip": {
            "ko": "이미지 저장 (Ctrl+S)",
            "en": "Save image (Ctrl+S)",
        },
        "save_confirm_title": {
            "ko": "저장 확인",
            "en": "Save Confirmation",
        },
        "save_confirm_msg": {
            "ko": "'{name}' 파일의 변경 내용을 저장하시겠습니까?",
            "en": "Do you want to save changes to '{name}'?",
        },
        "save_success": {
            "ko": "저장 완료: {path}",
            "en": "Saved: {path}",
        },
        "save_fail": {
            "ko": "이미지 저장에 실패했습니다.",
            "en": "Failed to save image.",
        },

        # History Actions
        "act_undo_tip": {
            "ko": "실행 취소 (Ctrl+Z)",
            "en": "Undo (Ctrl+Z)",
        },
        "act_redo_tip": {
            "ko": "다시 실행 (Ctrl+Y / Ctrl+Shift+Z)",
            "en": "Redo (Ctrl+Y / Ctrl+Shift+Z)",
        },
        "status_undone": {
            "ko": "실행 취소됨",
            "en": "Undone",
        },
        "status_no_undo": {
            "ko": "더 이상 실행 취소할 수 없습니다.",
            "en": "Nothing to undo",
        },
        "status_redone": {
            "ko": "다시 실행됨",
            "en": "Redone",
        },
        "status_no_redo": {
            "ko": "더 이상 다시 실행할 수 없습니다.",
            "en": "Nothing to redo",
        },

        # Canvas Transformations
        "act_resize_tip": {
            "ko": "캔버스 크기 조정 (Ctrl+Alt+C)",
            "en": "Adjust canvas size (Ctrl+Alt+C)",
        },
        "act_adjust_tip": {
            "ko": "색상/톤 보정 (Ctrl+U)",
            "en": "Color/tone adjustment (Ctrl+U)",
        },
        "act_rotate_tip": {
            "ko": "시계방향 90° 회전",
            "en": "Rotate clockwise 90°",
        },
        "act_flip_h_tip": {
            "ko": "좌우 대칭 반전",
            "en": "Flip horizontally",
        },
        "act_flip_v_tip": {
            "ko": "상하 대칭 반전",
            "en": "Flip vertically",
        },
        "act_grid_tip": {
            "ko": "격자 표시 토글 (Ctrl+')",
            "en": "Toggle grid (Ctrl+')",
        },
        "grid_combo_tip": {
            "ko": "격자 간격",
            "en": "Grid spacing",
        },
        "act_settings_tip": {
            "ko": "환경설정",
            "en": "Settings",
        },

        # Tool Names & Tips
        "tool_select": {
            "ko": "도형 선택",
            "en": "Shape Select",
        },
        "tool_select_tip": {
            "ko": "도형 선택 및 조절 (V)",
            "en": "Select and transform shape (V)",
        },
        "tool_select_area": {
            "ko": "영역 선택",
            "en": "Area Select",
        },
        "tool_select_area_tip": {
            "ko": "사각 영역 선택 (M)",
            "en": "Rectangular selection (M)",
        },
        "tool_select_lasso": {
            "ko": "올가미 선택",
            "en": "Lasso Select",
        },
        "tool_select_lasso_tip": {
            "ko": "자유 영역 올가미 선택 (L)",
            "en": "Freehand lasso selection (L)",
        },
        "tool_select_wand": {
            "ko": "자동 선택",
            "en": "Wand Select",
        },
        "tool_select_wand_tip": {
            "ko": "유사 색상 자동 선택 (W)",
            "en": "Magic wand auto selection (W)",
        },
        "tool_brush": {
            "ko": "브러시",
            "en": "Brush",
        },
        "tool_brush_tip": {
            "ko": "부드러운 브러시 (B)",
            "en": "Smooth brush (B)",
        },
        "tool_pencil": {
            "ko": "연필",
            "en": "Pencil",
        },
        "tool_pencil_tip": {
            "ko": "픽셀 연필 (N)",
            "en": "Pixel pencil (N)",
        },
        "tool_eraser": {
            "ko": "지우개",
            "en": "Eraser",
        },
        "tool_eraser_tip": {
            "ko": "지우개 (E)",
            "en": "Eraser (E)",
        },
        "tool_flood_fill": {
            "ko": "페인트통",
            "en": "Paint Bucket",
        },
        "tool_flood_fill_tip": {
            "ko": "색상 채우기 (G)",
            "en": "Paint bucket fill (G)",
        },
        "tool_eyedropper": {
            "ko": "스포이드",
            "en": "Eyedropper",
        },
        "tool_eyedropper_tip": {
            "ko": "색상 추출 스포이드 (I)",
            "en": "Eyedropper color picker (I)",
        },
        "tool_mosaic": {
            "ko": "모자이크",
            "en": "Mosaic",
        },
        "tool_mosaic_tip": {
            "ko": "영역 모자이크 처리 (J)",
            "en": "Pixelate selected area (J)",
        },
        "tool_step_badge": {
            "ko": "순서 배지",
            "en": "Step Badge",
        },
        "tool_step_badge_tip": {
            "ko": "순서 번호 배지 삽입 (K)",
            "en": "Insert sequential step badge (K)",
        },
        "tool_text": {
            "ko": "텍스트",
            "en": "Text",
        },
        "tool_text_tip": {
            "ko": "텍스트 입력 및 서식 (T)",
            "en": "Text input and formatting (T)",
        },
        "tool_shape_rect": {
            "ko": "직사각형",
            "en": "Rectangle",
        },
        "tool_shape_rect_tip": {
            "ko": "직사각형 삽입 (U)",
            "en": "Insert rectangle (U)",
        },
        "tool_shape_rounded_rect": {
            "ko": "둥근 직사각형",
            "en": "Rounded Rectangle",
        },
        "tool_shape_rounded_rect_tip": {
            "ko": "둥근 모서리 사각형 삽입",
            "en": "Insert rounded rectangle",
        },
        "tool_shape_arrow": {
            "ko": "화살표",
            "en": "Arrow",
        },
        "tool_shape_arrow_tip": {
            "ko": "화살표 삽입 (A)",
            "en": "Insert arrow (A)",
        },
        "tool_arrow_single": {
            "ko": "단방향 직선 화살표 (➡️)",
            "en": "Single Straight Arrow (➡️)",
        },
        "tool_arrow_double": {
            "ko": "양방향 직선 화살표 (↔️)",
            "en": "Double Straight Arrow (↔️)",
        },
        "tool_arrow_curved_single": {
            "ko": "단방향 곡선 화살표 (↪️)",
            "en": "Curved Single Arrow (↪️)",
        },
        "tool_arrow_curved_double": {
            "ko": "양방향 곡선 화살표 (🔄)",
            "en": "Curved Double Arrow (🔄)",
        },
        "tool_shape_ellipse": {
            "ko": "타원",
            "en": "Ellipse",
        },
        "tool_shape_ellipse_tip": {
            "ko": "타원 삽입",
            "en": "Insert ellipse",
        },
        "tool_shape_line": {
            "ko": "직선",
            "en": "Line",
        },
        "tool_shape_line_tip": {
            "ko": "직선 삽입",
            "en": "Insert line",
        },

        # Tool Properties
        "prop_tools_title": {
            "ko": "도구 모음",
            "en": "Tools",
        },
        "prop_props_title": {
            "ko": "도구 속성",
            "en": "Properties",
        },
        "prop_stroke": {
            "ko": " 굵기: ",
            "en": " Size: ",
        },
        "prop_stroke_tip": {
            "ko": "선/브러시 굵기 조절 (드래그 가능)",
            "en": "Stroke/brush width (Draggable)",
        },
        "prop_color1": {
            "ko": " 색상 1",
            "en": " Color 1",
        },
        "prop_color1_tip": {
            "ko": "색상 1 (선 / 전경색)",
            "en": "Color 1 (Stroke / Foreground)",
        },
        "prop_color2": {
            "ko": " 색상 2",
            "en": " Color 2",
        },
        "prop_color2_tip": {
            "ko": "색상 2 (채우기 / 배경색)",
            "en": "Color 2 (Fill / Background)",
        },
        "prop_opacity": {
            "ko": " 불투명도: ",
            "en": " Opacity: ",
        },
        "prop_opacity_tip": {
            "ko": "선택 색상 불투명도 조절",
            "en": "Adjust color opacity",
        },
        "prop_threshold": {
            "ko": " 임계값: ",
            "en": " Threshold: ",
        },
        "prop_threshold_tip": {
            "ko": "도구 옵션 수치 조절",
            "en": "Adjust tool option value",
        },
        "prop_step_start": {
            "ko": " 시작 번호: ",
            "en": " Start No: ",
        },
        "prop_step_start_tip": {
            "ko": "순서 배지 시작 번호 (기본: 1)",
            "en": "Step badge start number (Default: 1)",
        },
        "prop_block_size": {
            "ko": " 블록 크기: ",
            "en": " Block Size: ",
        },
        "prop_block_size_tip": {
            "ko": "모자이크 블록 크기 (픽셀 단위)",
            "en": "Mosaic block size (pixels)",
        },
        "prop_corner_radius": {
            "ko": " 모서리 곡률: ",
            "en": " Corner Radius: ",
        },
        "prop_corner_radius_tip": {
            "ko": "둥근 사각형 모서리 둥글기",
            "en": "Rounded rectangle corner radius",
        },
        "badge_type_number": {
            "ko": "① 숫자 (1, 2, 3...)",
            "en": "① Numbers (1, 2, 3...)",
        },
        "badge_type_alpha_upper": {
            "ko": "② 알파벳 대문자 (A, B, C...)",
            "en": "② Uppercase Letters (A, B, C...)",
        },
        "badge_type_alpha_lower": {
            "ko": "③ 알파벳 소문자 (a, b, c...)",
            "en": "③ Lowercase Letters (a, b, c...)",
        },
        "prop_all_layers": {
            "ko": " 모든 레이어 고려",
            "en": " Sample All Layers",
        },
        "prop_all_layers_tip": {
            "ko": "화면에 보이는 모든 레이어의 경계 참조",
            "en": "Sample boundaries from all visible layers",
        },
        "prop_trans_select": {
            "ko": "투명 선택",
            "en": "Trans. Select",
        },
        "prop_trans_select_tip": {
            "ko": "투명한 영역 선택 토글",
            "en": "Toggle transparent selection",
        },
        "prop_pixel_snap": {
            "ko": "픽셀 스냅",
            "en": "Pixel Snap",
        },
        "prop_pixel_snap_tip": {
            "ko": "정수 픽셀 스냅 토글",
            "en": "Toggle integer pixel snap",
        },

        # Docks
        "dock_tools_title": {
            "ko": "도구 및 속성",
            "en": "Tools & Properties",
        },
        "dock_layers_title": {
            "ko": "레이어 및 도형 계층",
            "en": "Layers & Shapes",
        },

        # Layer Panel Controls
        "layer_tab_all": {
            "ko": "ALL",
            "en": "ALL",
        },
        "layer_tab_layers": {
            "ko": "레이어",
            "en": "Layers",
        },
        "layer_tab_shapes": {
            "ko": "도형",
            "en": "Shapes",
        },
        "layer_add": {
            "ko": "+ 추가",
            "en": "+ Add",
        },
        "layer_add_tip": {
            "ko": "새 레이어 추가",
            "en": "Add new layer",
        },
        "layer_del": {
            "ko": "- 삭제",
            "en": "- Delete",
        },
        "layer_del_tip": {
            "ko": "선택 레이어/도형 삭제",
            "en": "Delete selected layer/shape",
        },
        "layer_up_tip": {
            "ko": "위로 이동",
            "en": "Move up",
        },
        "layer_down_tip": {
            "ko": "아래로 이동",
            "en": "Move down",
        },
        "layer_bg_default": {
            "ko": "배경 레이어",
            "en": "Background Layer",
        },
        "layer_shape_default": {
            "ko": "기본 도형 레이어",
            "en": "Default Shape Layer",
        },
        "layer_new_prefix": {
            "ko": "새 레이어",
            "en": "New Layer",
        },
        "layer_indent": {
            "ko": "📁 하위 레이어로 묶기",
            "en": "📁 Group as Sub-layer",
        },
        "layer_outdent": {
            "ko": "📂 상위 레이어로 꺼내기",
            "en": "📂 Ungroup from Parent",
        },
        "cat_rect": {
            "ko": "직사각형",
            "en": "Rectangles",
        },
        "cat_ellipse": {
            "ko": "타원",
            "en": "Ellipses",
        },
        "cat_line": {
            "ko": "직선",
            "en": "Lines",
        },
        "menu_edit_text": {
            "ko": "✏️ 텍스트 내용 수정",
            "en": "✏️ Edit Text Content",
        },
        "menu_merge_down": {
            "ko": "⬇️ 아래 레이어와 병합",
            "en": "⬇️ Merge Down",
        },
        "menu_merge_raster": {
            "ko": "🎨 아래 래스터 레이어에 병합",
            "en": "🎨 Merge into Raster Layer Below",
        },
        "menu_bring_front": {
            "ko": "⬆️ 맨 앞으로 가져오기",
            "en": "⬆️ Bring to Front",
        },
        "menu_send_back": {
            "ko": "⬇️ 맨 뒤로 보내기",
            "en": "⬇️ Send to Back",
        },
        "menu_del_shape": {
            "ko": "🗑️ 도형 삭제",
            "en": "🗑️ Delete Shape",
        },
        "menu_add_layer": {
            "ko": "➕ 새 레이어 추가",
            "en": "➕ Add New Layer",
        },
        "menu_del_layer": {
            "ko": "🗑️ 레이어 삭제",
            "en": "🗑️ Delete Layer",
        },
        "warn_cant_delete_shape": {
            "ko": "기본 도형 레이어는 삭제할 수 없습니다.",
            "en": "Cannot delete default shape layer.",
        },
        "warn_min_one_layer": {
            "ko": "최소 1개 이상의 레이어가 유지되어야 합니다.",
            "en": "At least one layer must be maintained.",
        },

        # Status Bar
        "status_tool": {
            "ko": "도구: {name}",
            "en": "Tool: {name}",
        },
        "status_canvas_size": {
            "ko": "캔버스: {w} × {h} px",
            "en": "Canvas: {w} × {h} px",
        },
        "status_zoom": {
            "ko": "배율: {zoom}%",
            "en": "Zoom: {zoom}%",
        },
        "status_coord": {
            "ko": "X: {x}, Y: {y} px",
            "en": "X: {x}, Y: {y} px",
        },
        "status_shape_selected": {
            "ko": "도형 선택됨: Enter 키 또는 더블클릭으로 레이어에 고정, Esc 키로 선택 해제",
            "en": "Shape selected: Press Enter or double-click to place onto layer, Esc to deselect",
        },
        "status_shape_merged": {
            "ko": "도형을 바로 아래 래스터 레이어에 병합했습니다.",
            "en": "Shape merged into raster layer directly below.",
        },
        "status_layer_merged_down": {
            "ko": "레이어를 바로 아래 래스터 레이어에 병합했습니다.",
            "en": "Layer merged into raster layer directly below.",
        },
        "status_text_created": {
            "ko": "텍스트 레이어를 생성했습니다.",
            "en": "Text layer created.",
        },
        "dlg_text_title": {
            "ko": "텍스트 입력 및 편집",
            "en": "Text Input & Editing",
        },
        "dlg_text_prompt": {
            "ko": "캔버스에 삽입할 텍스트를 입력하세요:",
            "en": "Enter the text to place on canvas:",
        },
        "prop_font_size": {
            "ko": "글꼴 크기",
            "en": "Font Size",
        },

        # Canvas HUD
        "hud_zoom_in_tip": {
            "ko": "캔버스 확대 (Ctrl++)",
            "en": "Zoom in (Ctrl++)",
        },
        "hud_zoom_out_tip": {
            "ko": "캔버스 축소 (Ctrl+-)",
            "en": "Zoom out (Ctrl+-)",
        },
        "hud_reset_tip": {
            "ko": "100% 뷰 리셋 (Ctrl+0)",
            "en": "Reset to 100% (Ctrl+0)",
        },
        "hud_grid_tip": {
            "ko": "격자 가이드 표시 토글 (Ctrl+')",
            "en": "Toggle grid guide (Ctrl+')",
        },
        "hud_grid_combo_tip": {
            "ko": "격자 간격 (직접 입력 또는 선택)",
            "en": "Grid spacing (Type or select)",
        },
        "hud_rotate_tip": {
            "ko": "캔버스 시계방향 90° 회전 (현재: {rot}°)",
            "en": "Rotate canvas 90° clockwise (Current: {rot}°)",
        },
        "hud_flip_h_tip": {
            "ko": "캔버스 좌우 대칭 반전 (수평)",
            "en": "Flip canvas horizontally",
        },
        "hud_flip_v_tip": {
            "ko": "캔버스 상하 대칭 반전 (수직)",
            "en": "Flip canvas vertically",
        },

        # Settings Dialog
        "settings_title": {
            "ko": "설정",
            "en": "Settings",
        },
        "tab_general": {
            "ko": "기본 설정",
            "en": "General",
        },
        "tab_patch": {
            "ko": "업데이트 내역",
            "en": "Release Notes",
        },
        "patch_notes_content": {
            "ko": (
                "🎉 [ Paint Essential v1.3.0 신규 업데이트 및 전체 최적화 안내 ]\n\n"
                "• 전체적인 성능 최적화 및 렌더링 파이프라인 개편:\n"
                "  - 스마트 뷰포트 갱신(SmartViewportUpdate) 적용으로 4K/고해상도 환경에서 렌더링 부하 최소화\n"
                "  - 스트로크 실시간 드로잉 이벤트 쓰로틀링 적용으로 브러시/연필/지우개 래그 제로화 달성\n"
                "  - 스포이드 돋보기 실시간 합성 레이어 캐싱 적용으로 마우스 호버 시 CPU 사용량 대폭 경감\n\n"
                "• 텍스트 입력 기능 완성 및 클립보드 붙여넣기 안정화:\n"
                "  - 텍스트 도구(T)를 통한 폰트 크기/서체/스타일 실시간 편집 다이얼로그 지원\n"
                "  - 장문의 멀티라인 텍스트 붙여넣기 시 크래시 없는 견고한 바운딩 박스 자동 측정 지원\n\n"
                "• 선택 영역 삭제 및 Delete 키 동작 고도화:\n"
                "  - Delete 키 입력 시 점선 선택 영역(Marquee)은 유지하면서 내부 이미지/도형만 깔끔하게 삭제\n"
                "  - 투명 선택 토글 OFF 시 서브 컬러(색 2 / 배경색) 유지, 토글 ON 시 투명화 삭제 연동\n"
                "  - 도형 레이어가 활성화된 상태에서도 선택 영역 내부의 이미지 및 도형 정확히 감지 및 삭제\n\n"
                "• 우클릭 도형 그리기 및 팝업 버그 해결:\n"
                "  - 우클릭 드래그 도형 생성 직후 불필요하게 뜨던 컨텍스트 메뉴 팝업 억제\n"
                "  - 도형 팝업 닫기(바깥 클릭) 시 텍스트 다이얼로그가 돌발 실행되던 버그 완벽 수정\n\n"
                "--------------------------------------------------\n"
                "🛠️ [ Paint Essential v1.2.2 마이너 패치 안내 ]\n\n"
                "• 바로 아래 래스터 레이어로의 병합 로직 개편:\n"
                "  - 도형 병합 시 배경 레이어가 아닌 바로 아래 위치한 래스터 레이어로 정확히 병합\n"
                "  - 중간에 다른 도형 레이어가 있더라도 도형은 건너뛰고 반드시 래스터 레이어에만 안전하게 병합\n"
                "  - 래스터 레이어 패널 및 Ctrl+E 단축키를 통한 '아래 레이어와 병합(Merge Down)' 기능 신규 지원\n\n"
                "--------------------------------------------------\n"
                "🛠️ [ Paint Essential v1.2.1 마이너 패치 안내 ]\n\n"
                "• 도형 자동 래스터라이즈(병합) 버그 수정:\n"
                "  - 도형 크기/위치 조절 후 바깥 영역 클릭 시 레이어에 강제 병합되던 현상 해결\n"
                "  - 도형은 계속 독립된 벡터 레이어로 유지되며, Enter/더블클릭/메뉴로만 명시적 병합\n"
                "• 다크 모드 스크롤바 가시성 개선:\n"
                "  - 다크 모드 환경에서 스크롤바가 눈에 잘 띄도록 소프트 스카이 블루(#60a5fa) 스타일 적용\n\n"
                "--------------------------------------------------\n"
                "🎉 [ Paint Essential v1.2.0 업데이트 안내 ]\n\n"
                "더욱 직관적이고 편리한 그래픽 편집을 위해 새로운 도구와 편의 기능을 선보입니다.\n\n"
                "✨ 주요 새로운 기능 (v1.2.0):\n"
                "• 스마트 도구 옵션 바:\n"
                "  - 순서 배지(K): 시작 번호 설정 및 숫자(1, 2...), 영문 대/소문자(A, B... / a, b...) 스타일 지원\n"
                "  - 모자이크(J): 원하는 블록 크기(4~64px)를 자유롭게 조절하여 적용\n"
                "  - 둥근 사각형: 모서리 둥글기(곡률)를 수치로 정밀하게 조절\n\n"
                "• 도구 모음 그룹화 및 확장:\n"
                "  - 사각형(U): 우클릭 또는 길게 눌러 직사각형과 둥근 사각형을 손쉽게 전환\n"
                "  - 화살표(A): 직선/곡선 및 단방향/양방향 화살표를 지원하며, 곡선 핸들로 모양 조절 가능\n\n"
                "• 깔끔한 복사 안내 알림:\n"
                "  - 복사(Ctrl+C), 투명 PNG 복사(Ctrl+Shift+C), 잘라내기(Ctrl+X) 시 화면 상단에 친절한 안내 메시지 표시\n\n"
                "--------------------------------------------------\n"
                "📋 [ 이전 업데이트 내역 (v1.1.0) ]\n"
                "• 화살표 도구(A), 모자이크 도구(J), 순서 배지 도구(K) 추가\n"
                "• 스포이드 색상 추출 시 픽셀 확대 돋보기 지원\n"
                "• 투명 배경을 유지한 클립보드 복사(Ctrl+Shift+C) 기능 추가\n"
                "• 레이어 목록 필터 탭 (전체 / 레이어 / 도형) 제공\n\n"
                "--------------------------------------------------\n"
                "🌱 [ 최초 릴리즈 (v1.0.0) ]\n"
                "• 가볍고 빠른 무설치(포터블) 스마트 그래픽 에디터\n"
                "• 고해상도 디스플레이 완벽 지원 및 다크 모드/라이트 모드 지원"
            ),
            "en": (
                "🎉 [ Paint Essential v1.3.0 Release & Performance Optimization ]\n\n"
                "• Full Rendering Pipeline & Performance Optimization:\n"
                "  - Smart Viewport Updates (SmartViewportUpdate) minimizing rendering overhead on 4K/High-DPI displays\n"
                "  - Real-time drawing event throttling eliminating brush/pencil/eraser input lag\n"
                "  - Eyedropper composite layer caching significantly reducing CPU usage during mouse hover\n\n"
                "• Text Tool Implementation & Robust Clipboard Paste:\n"
                "  - Text tool (T) dialog for font size, family, and styling adjustments\n"
                "  - Hardened multiline text clipboard paste with auto-sizing bounds and zero-crash guarantees\n\n"
                "• Area Image Deletion & Delete Key Modernization:\n"
                "  - Pressing Delete erases image & shapes inside selection while keeping the marquee box active\n"
                "  - Secondary color preserved when transparent selection is OFF, and transparent when ON\n"
                "  - Reliable content deletion even when vector shape layer is currently active\n\n"
                "• Right-Click Shape & Context Menu Enhancements:\n"
                "  - Suppressed intrusive context menu popup upon finishing right-click shape creation\n"
                "  - Fixed unexpected text dialog popup when dismissing shape context menu\n\n"
                "--------------------------------------------------\n"
                "🛠️ [ Paint Essential v1.2.2 Minor Patch Notes ]\n\n"
                "• Accurate Merge-Down into Raster Layer Below:\n"
                "  - Shapes now merge into the raster layer directly below them in the stack instead of falling back to background\n"
                "  - Skips any intermediate shape layers to ensure baking strictly into a bitmap raster canvas\n"
                "  - Added Merge Down support for raster layers via context menu & Ctrl+E shortcut\n\n"
                "--------------------------------------------------\n"
                "🛠️ [ Paint Essential v1.2.1 Minor Patch Notes ]\n\n"
                "• Fixed Shape Auto-Rasterize Issue:\n"
                "  - Shapes no longer auto-merge to raster layer when clicking outside\n"
                "  - Shapes remain as independent vector layers and only merge via Enter/Double-click/Menu\n"
                "• Enhanced Dark Mode Scrollbar Visibility:\n"
                "  - Soft sky blue (#60a5fa) scrollbar styling with responsive hover & pressed feedback\n\n"
                "--------------------------------------------------\n"
                "🎉 [ Paint Essential v1.2.0 Release Notes ]\n\n"
                "Introducing new tools and workflow enhancements for a smoother creative experience.\n\n"
                "✨ Highlights in v1.2.0:\n"
                "• Smart Tool Options:\n"
                "  - Step Badge (K): Choose start number & badge styles (Numbers, Uppercase/Lowercase letters)\n"
                "  - Mosaic (J): Adjust pixel block size (4~64px) dynamically for blurring areas\n"
                "  - Rounded Rectangle: Fine-tune corner radius with real-time numeric controls\n\n"
                "• Tool Grouping & Expansion:\n"
                "  - Rectangle (U): Right-click or long-press to switch between Rectangle & Rounded Rectangle\n"
                "  - Arrow (A): Choose Straight / Curved & Single / Double arrows with custom curve handles\n\n"
                "• Clean Clipboard Feedback:\n"
                "  - Floating notification banners for Copy (Ctrl+C), Transparent Copy (Ctrl+Shift+C), and Cut (Ctrl+X)\n\n"
                "--------------------------------------------------\n"
                "📋 [ Previous Release (v1.1.0) ]\n"
                "• Added Arrow Tool (A), Mosaic Tool (J), and Step Badge Tool (K)\n"
                "• Eyedropper with precision pixel magnifier\n"
                "• Copy with transparency support (Ctrl+Shift+C)\n"
                "• Layer panel filter tabs (ALL / Layers / Shapes)\n\n"
                "--------------------------------------------------\n"
                "🌱 [ Initial Release (v1.0.0) ]\n"
                "• Fast, lightweight, and fully portable graphic editor\n"
                "• High-DPI display support with sleek Light & Dark themes"
            ),
        },
        "tab_credits": {
            "ko": "크레딧",
            "en": "Credits",
        },
        "credits_sub_label": {
            "ko": "가볍고 빠른 스마트 그래픽 에디터",
            "en": "Lightweight & Powerful Smart Graphic Editor",
        },
        "group_language": {
            "ko": "언어 설정",
            "en": "Language",
        },
        "lang_ko": {
            "ko": "한국어",
            "en": "Korean",
        },
        "lang_en": {
            "ko": "English",
            "en": "English",
        },
        "group_theme": {
            "ko": "화면 테마",
            "en": "Theme",
        },
        "theme_light": {
            "ko": "라이트 모드",
            "en": "Light Mode",
        },
        "theme_dark": {
            "ko": "다크 모드",
            "en": "Dark Mode",
        },
        "btn_ok": {
            "ko": "확인",
            "en": "OK",
        },
        "credits_author_label": {
            "ko": "제작 및 개발",
            "en": "Developed by",
        },
        "credits_engine_label": {
            "ko": "그래픽 엔진",
            "en": "Graphics Engine",
        },
        "credits_version_label": {
            "ko": "버전 정보",
            "en": "Version",
        },

        # Interaction & UX Options
        "group_interaction": {
            "ko": "상호작용 및 UX",
            "en": "Interaction & UX",
        },
        "opt_ghost_indicator": {
            "ko": "도형 확정 예고 (고스트 인디케이터)",
            "en": "Shape Commit Preview (Ghost Indicator)",
        },
        "tooltip_ghost_indicator": {
            "ko": "도형 선택 시 빈 공간에 마우스를 올리면 픽셀 고정 안내를 표시하고, 클릭 시 레이어에 즉시 병합합니다.",
            "en": "Displays commit preview badge when hovering empty canvas, and merges shape into layer upon clicking outside.",
        },
        "ghost_commit_badge": {
            "ko": "✓ 클릭 시 픽셀 고정",
            "en": "✓ Click to bake pixels",
        },
        "status_ghost_enabled": {
            "ko": "도형 확정 예고(고스트 인디케이터)가 활성화되었습니다.",
            "en": "Ghost Indicator preview enabled",
        },
        "status_ghost_disabled": {
            "ko": "도형 확정 예고(고스트 인디케이터)가 비활성화되었습니다.",
            "en": "Ghost Indicator preview disabled",
        },

        # Adjustment Dialog
        "adjust_title": {
            "ko": "색상/톤 보정",
            "en": "Color/Tone Adjustment",
        },
        "adjust_empty": {
            "ko": "아무것도 선택되지 않음",
            "en": "Nothing Selected",
        },
        "adjust_preview": {
            "ko": "실시간 미리보기",
            "en": "Live Preview",
        },
        "adjust_large_btn": {
            "ko": "🔍 크게 보기",
            "en": "🔍 Large Preview",
        },
        "adjust_hue": {
            "ko": "색조 (Hue):",
            "en": "Hue:",
        },
        "adjust_sat": {
            "ko": "채도 (Sat):",
            "en": "Saturation:",
        },
        "adjust_bright": {
            "ko": "명도 (Bright):",
            "en": "Brightness:",
        },
        "adjust_contrast": {
            "ko": "대비 (Contrast):",
            "en": "Contrast:",
        },
        "adjust_layers": {
            "ko": "대상 레이어",
            "en": "Target Layers",
        },
        "adjust_select_all": {
            "ko": "전체 선택",
            "en": "Select All",
        },
        "adjust_reset": {
            "ko": "초기화",
            "en": "Reset",
        },
        "btn_cancel": {
            "ko": "취소",
            "en": "Cancel",
        },

        # Anchor Resize Dialog
        "anchor_title": {
            "ko": "캔버스 크기 조정 (축 설정)",
            "en": "Canvas Size (Anchor Pivot)",
        },
        "anchor_curr_size": {
            "ko": "현재 캔버스 크기: {w} × {h} px",
            "en": "Current Size: {w} × {h} px",
        },
        "anchor_new_size": {
            "ko": "새 캔버스 크기",
            "en": "New Canvas Size",
        },
        "anchor_width": {
            "ko": "너비 (W):",
            "en": "Width (W):",
        },
        "anchor_height": {
            "ko": "높이 (H):",
            "en": "Height (H):",
        },
        "anchor_keep_ratio": {
            "ko": "가로세로 비율 유지",
            "en": "Maintain Aspect Ratio",
        },
        "anchor_pivot": {
            "ko": "기준 축 설정 (Anchor Pivot)",
            "en": "Anchor Pivot",
        },
    }

    @classmethod
    def get_language(cls) -> str:
        return cls._current_language

    @classmethod
    def set_language(cls, lang: str):
        if lang in ("ko", "en"):
            cls._current_language = lang

    @classmethod
    def tr(cls, key: str, lang: Optional[str] = None, **kwargs) -> str:
        target_lang = lang or cls._current_language
        entry = cls.TRANSLATIONS.get(key)
        if not entry:
            return key
        text = entry.get(target_lang, entry.get("ko", key))
        if kwargs:
            try:
                text = text.format(**kwargs)
            except Exception:
                pass
        return text
