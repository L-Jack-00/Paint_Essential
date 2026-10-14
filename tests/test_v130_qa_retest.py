"""
Paint Essential v1.3.0 QA Deep Re-Test Script
Executing empirical validation across 5 core focus areas and regression gates.
"""
import sys
import os
import time

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPoint, QPointF, QRectF, QRect
from PyQt6.QtGui import QColor, QImage, QPainter, QMouseEvent, QKeyEvent

from core.layer_manager import LayerManager, LayerType, ShapeItemData
from core.history_manager import HistoryManager
from core.input_safety import InputSafetyTracker, InputMode
from core.image_processor import ImageProcessor
from ui.canvas_view import CanvasView
from ui.main_window import MainWindow
from ui.shape_items import TransformableShapeItem

def run_retest():
    app = QApplication.instance() or QApplication(sys.argv)
    results = {}

    print("=== [1] 텍스트 도구(T) 및 대용량 멀티라인 붙여넣기 무결성 검증 ===")
    win = MainWindow()
    cv = win.canvas_view
    lm = win.layer_manager
    hm = win.history_manager

    # 1-1. 폰트 속성 및 다이얼로그 프로퍼티
    win.tool_actions[InputMode.TEXT].trigger()
    assert win.input_safety.current_mode == InputMode.TEXT, "Text tool activation failed"
    assert "글꼴 크기" in win.threshold_label.text(), "Font size label missing"
    assert win.threshold_spin.minimum() == 8 and win.threshold_spin.maximum() == 144, "Font size range invalid"

    # 1-2. 대용량 멀티라인 + 특수문자 + 이모지 텍스트
    large_multiline_text = "\n".join([f"라인 #{i}: Paint Essential v1.3.0 🚀 ✨ [Special: 漢字 / ひらがな / #!@$%^&*()]" for i in range(100)])
    text_data = ShapeItemData(
        id="text_large_stress",
        shape_type="text",
        x=20, y=20,
        width=500, height=2000,
        stroke_color="#1a56db",
        meta={
            "text": large_multiline_text,
            "font_size": 16,
            "font_family": "Malgun Gothic",
            "font_bold": True,
            "font_italic": False
        }
    )
    t_start = time.perf_counter()
    shape_item = TransformableShapeItem(text_data)
    test_img = QImage(1200, 2500, QImage.Format.Format_ARGB32_Premultiplied)
    test_img.fill(0)
    p = QPainter(test_img)
    from PyQt6.QtWidgets import QStyleOptionGraphicsItem
    shape_item.paint(p, QStyleOptionGraphicsItem())
    p.end()
    t_elapsed = (time.perf_counter() - t_start) * 1000
    print(f"  -> 100줄 멀티라인/특수문자/이모지 렌더링 소요시간: {t_elapsed:.2f}ms (크래시 0)")
    assert shape_item.width > 0 and shape_item.height > 0
    results["Area 1: Text Tool & Multiline Stress"] = f"PASS ({t_elapsed:.2f}ms, 100 lines painted without crash)"

    print("=== [2] 도형 우클릭 생성 및 팝업 버그 방어 검증 ===")
    # 2-1. 우클릭 드래그 도형 생성 시 컨텍스트 메뉴 억제
    win.input_safety.current_mode = InputMode.SHAPE_RECT
    cv.drag_start_pt = QPointF(10, 10)
    rel_ev = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPointF(80, 80),
        Qt.MouseButton.RightButton,
        Qt.MouseButton.RightButton,
        Qt.KeyboardModifier.NoModifier
    )
    cv.mouseReleaseEvent(rel_ev)
    assert cv._suppress_context_menu is True, "_suppress_context_menu flag must be True after right-click drag"
    
    # 2-2. 컨텍스트 메뉴 이벤트 수신 시 억제 및 플래그 리셋 확인
    from unittest.mock import MagicMock
    from PyQt6.QtGui import QContextMenuEvent
    mock_ctx = MagicMock(spec=QContextMenuEvent)
    cv.contextMenuEvent(mock_ctx)
    mock_ctx.accept.assert_called_once()
    assert cv._suppress_context_menu is False, "Flag must be consumed and reset"

    # 2-3. 도형 팝업 닫을 때 텍스트 편집창 돌발 실행 방지
    s_item = TransformableShapeItem(ShapeItemData(id="rect_pop", shape_type="rect", x=10, y=10, width=50, height=50))
    edit_text_mock = MagicMock()
    s_item.on_edit_text_cb = edit_text_mock
    from PyQt6.QtWidgets import QMenu
    from unittest.mock import patch
    ctx_ev = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(20, 20), QPoint(20, 20))
    with patch.object(QMenu, 'exec', return_value=None):
        s_item.contextMenuEvent(ctx_ev)
    edit_text_mock.assert_not_called()
    print("  -> 우클릭 도형 생성 시 팝업 억제 및 팝업 닫기 시 텍스트 다이얼로그 오작동 방어 성공")
    results["Area 2: Right-Click Shape & Popup Defense"] = "PASS (Context menu suppressed, no rogue text dialog)"

    print("=== [3] 선택 영역(Marquee) 내부 이미지 삭제 (Delete 키) 검증 ===")
    # 3-1. 점선 선택 영역(Marquee) 유지 확인
    # 3-2. 투명 선택 OFF: 보조색(Color 2) 채우기 확인
    bg_layer = lm.get_layer("bg_layer")
    lm.active_layer_id = bg_layer.id
    bg_layer.raster_image.fill(QColor(255, 0, 0, 255)) # Red
    cv.secondary_color = QColor(0, 255, 0, 255) # Green
    cv.transparent_selection_enabled = False
    cv.selection_rect = QRectF(20, 20, 30, 30)

    cv.delete_selection()
    assert cv.selection_rect is not None, "Selection marquee rect must NOT disappear on Delete"
    assert cv.selection_rect == QRectF(20, 20, 30, 30), "Selection bounds must remain intact"
    px_del = bg_layer.raster_image.pixelColor(25, 25)
    assert px_del == QColor(0, 255, 0, 255), f"Expected green secondary color fill, got {px_del.name()}"

    # 3-3. 투명 선택 ON: Alpha 0 완전 투명화 삭제 확인
    cv.transparent_selection_enabled = True
    cv.delete_selection()
    assert cv.selection_rect is not None, "Selection marquee still intact"
    px_trans = bg_layer.raster_image.pixelColor(25, 25)
    assert px_trans.alpha() == 0, f"Expected transparent pixel (alpha 0), got alpha {px_trans.alpha()}"

    # 3-4. 도형 레이어가 활성화된 상태에서 선택 영역 Delete 시 벡터 + 하부 래스터 동시 삭제
    s_del_data = ShapeItemData(id="del_target_shape", shape_type="rect", x=50, y=50, width=40, height=40)
    s_layer = lm.add_shape_to_default_layer(s_del_data)
    g_item = cv._create_shape_graphics_item(s_del_data)
    cv.shape_items[s_del_data.id] = g_item
    cv.selection_rect = QRectF(40, 40, 60, 60)
    cv.transparent_selection_enabled = False
    cv.secondary_color = QColor(0, 0, 255, 255) # Blue

    cv.delete_selection()
    assert s_del_data.id not in cv.shape_items, "Vector shape inside marquee must be deleted"
    assert g_item not in cv.scene.items(), "Vector shape item must be removed from QGraphicsScene"
    assert cv.selection_rect is not None, "Marquee persists"
    px_under = bg_layer.raster_image.pixelColor(55, 55)
    assert px_under == QColor(0, 0, 255, 255), "Raster underneath shape layer must also be cleared"
    print("  -> Delete 키: 점선 보존, 투명/불투명 분기, 도형+래스터 동시 삭제 ALL PASS")
    results["Area 3: Marquee Delete & Mode Branching"] = "PASS (Marquee intact, secondary color / alpha 0 / vector delete)"

    print("=== [4] 드로잉 성능 및 렌더링 파이프라인 검증 ===")
    # 4-1. 1,000pt 연속 드래그 시뮬레이션 및 프레임 레이트
    lm.active_layer_id = "bg_layer"
    win.input_safety.current_mode = InputMode.BRUSH
    cv.stroke_width = 5
    cv.primary_color = QColor(0, 0, 0, 255)
    cv.last_scene_pt = QPointF(10, 10)
    
    t_draw_start = time.perf_counter()
    for i in range(1, 1000):
        next_pt = QPointF(10 + (i % 200), 10 + (i // 5))
        cv._draw_raster_line(cv.last_scene_pt, next_pt)
        cv.last_scene_pt = next_pt
    t_draw_total = (time.perf_counter() - t_draw_start) * 1000
    avg_per_step = t_draw_total / 1000
    effective_fps = 1000.0 / avg_per_step if avg_per_step > 0 else 9999.0
    print(f"  -> 1,000회 연속 브러시 스트로크 총 소요: {t_draw_total:.2f}ms (단계당 {avg_per_step*1000:.1f}us, 환산 FPS: {effective_fps:.1f})")
    assert effective_fps > 60.0, f"Drawing throughput below 60 FPS: {effective_fps:.1f}"

    # 4-2. 스포이드 마우스 이동 시 돋보기(Loupe) 캐싱 검증
    win.input_safety.current_mode = InputMode.EYEDROPPER
    cv.invalidate_composite_cache()
    assert cv._cached_composite is None
    
    # First call creates cache
    img1 = cv.get_composite_image()
    assert img1 is not None and not img1.isNull()
    assert cv._cached_composite is img1, "First call must cache composite image"
    
    # Second call returns the exact same cached object (no recomposition!)
    img2 = cv.get_composite_image()
    assert img2 is img1, "Subsequent calls during eyedropper movement must reuse cached composite"
    print("  -> 드로잉 초고속 렌더링(60+ FPS 초과) 및 스포이드 돋보기 캐싱 재사용 확인 완료")
    results["Area 4: Performance & Rendering Pipeline"] = f"PASS (Effective {effective_fps:.1f} FPS, Loupe composite caching verified)"

    print("=== [5] 레이어 병합 및 히스토리(Undo/Redo 40단계) 검증 ===")
    # 5-1. Ctrl+E 아래 레이어 병합 시 중간 도형 레이어 건너뛰고 직하위 래스터로 병합
    lm_fresh = LayerManager(canvas_width=200, canvas_height=150)
    cv_fresh = CanvasView(lm_fresh, InputSafetyTracker(), HistoryManager())
    bg_fresh = lm_fresh.get_layer("bg_layer")
    bg_fresh.raster_image.fill(QColor(255, 255, 255, 255)) # White

    l_target = lm_fresh.add_layer("래스터 1")
    l_target.raster_image.fill(QColor(0, 0, 0, 0)) # Transparent

    s_middle = ShapeItemData(id="s_mid", shape_type="rect", x=10, y=10, width=20, height=20, fill_color="#ff0000")
    lm_fresh.add_shape_layer(s_middle)

    s_top = ShapeItemData(id="s_top", shape_type="rect", x=30, y=30, width=20, height=20, fill_color="#00ff00")
    lm_fresh.add_shape_layer(s_top)

    target_found = lm_fresh.find_raster_layer_below("s_top")
    assert target_found.id == l_target.id, f"Must skip s_mid and target l_target, got {target_found.id}"

    # Merge s_top
    cv_fresh.merge_shape_to_raster("s_top")
    assert l_target.raster_image.pixelColor(35, 35).green() > 200, "Pixels from s_top must bake into l_target"
    assert bg_fresh.raster_image.pixelColor(35, 35) == QColor(255, 255, 255, 255), "bg_layer must be untouched"

    # 5-2. 40단계 Undo/Redo 스트레스 테스트
    hm_stress = HistoryManager(max_steps=40)
    for step in range(1, 55):
        hm_stress.record_step(f"Step {step}", lambda: None, lambda: None, estimated_bytes=100)
    
    assert hm_stress.step_count == 40, f"Max undo limit 40 enforced, actual: {hm_stress.step_count}"
    assert "Step 15" in hm_stress.undo_stack[0].description, f"FIFO eviction correct, earliest step: {hm_stress.undo_stack[0].description}"

    # Rollback 40 steps
    for _ in range(40):
        assert hm_stress.can_undo() is True
        hm_stress.undo()
    assert hm_stress.can_undo() is False
    assert hm_stress.can_redo() is True

    # Redo 40 steps
    for _ in range(40):
        assert hm_stress.can_redo() is True
        hm_stress.redo()
    assert hm_stress.can_redo() is False
    print("  -> 도형 건너뛰기 래스터 병합 및 40단계 Undo/Redo FIFO 스트레스 무결성 ALL PASS")
    results["Area 5: Layer Merge & 40-step History Stress"] = "PASS (Skipped intermediate shapes, 40-step FIFO eviction perfect)"

    win.close()
    print("\n=======================================================")
    print("           [전수 정밀 QA 재검증 결과 요약]")
    print("=======================================================")
    for k, v in results.items():
        print(f"✔ {k}: {v}")
    print("=======================================================\n")
    return True

if __name__ == "__main__":
    success = run_retest()
    sys.exit(0 if success else 1)
