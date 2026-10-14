"""
Paint Pro - Standalone Executable Packaging & Sanitization Script
LJack Protocol Pillar 7: Release Sanitization & Zero-cruft Packaging
"""
import subprocess
import sys
import shutil
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def run_tests():
    print("[1/3] Running Headless Test Suite...")
    result = subprocess.run([sys.executable, "-m", "unittest", "discover", "tests"], capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ Test failure detected! Packaging aborted.")
        print(result.stdout)
        print(result.stderr)
        sys.exit(1)
    print("  ✔️ All unit tests passed with 0 defects.")


def clean_artifacts():
    print("[2/3] Cleaning temporary build artifacts...")
    for folder in ["build", "dist", "__pycache__"]:
        if os.path.exists(folder):
            shutil.rmtree(folder, ignore_errors=True)
    for root, dirs, files in os.walk("."):
        for f in files:
            if f.endswith((".spec", ".pyc", ".tmp", ".log")):
                try:
                    os.remove(os.path.join(root, f))
                except Exception:
                    pass
    print("  ✔️ Cleaned.")


def package_exe():
    print("[3/3] Compiling portable release via PyInstaller with isolated data directory...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=Paint Essential",
        "--windowed",
        "--onedir",
        "--clean",
        "--icon=ui/assets/app_icon.ico",
        "--add-data=ui/assets;ui/assets",
        "run.py"
    ]
    result = subprocess.run(cmd)
    if result.returncode == 0:
        dist_src = os.path.join("dist", "Paint Essential")
        portable_dir = os.path.join("dist", "PaintEssential_v1.3.0_Portable")
        if os.path.exists(portable_dir):
            shutil.rmtree(portable_dir, ignore_errors=True)
        shutil.copytree(dist_src, portable_dir)

        readme_path = os.path.join(portable_dir, "README.txt")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(
                "============================================================\n"
                "  🎨 Paint Essential (페인트 에센셜) v1.3.0\n"
                "============================================================\n\n"
                "• 제작 및 개발: L.Jack with Google Antigravity\n"
                "• 그래픽 엔진: Paint Essential Core Engine v1.3.0\n"
                "• 지원 환경: Windows 10 / 11 (64-bit)\n\n"
                "[ v1.3.0 신규 업데이트 및 전체 최적화 안내 ]\n"
                "1. 전체적인 성능 최적화 및 렌더링 파이프라인 개편:\n"
                "   - 스마트 뷰포트 갱신(SmartViewportUpdate)으로 4K/고해상도 환경에서 렌더링 부하 최소화\n"
                "   - 실시간 스트로크 드로잉 쓰로틀링 적용으로 브러시/연필/지우개 래그 제로화 달성\n"
                "   - 스포이드 픽셀 돋보기 실시간 합성 레이어 캐싱 적용으로 마우스 호버 시 CPU 사용량 대폭 경감\n\n"
                "2. 텍스트 입력 기능 완성 및 클립보드 붙여넣기 안정화:\n"
                "   - 텍스트 도구(T)를 통한 글꼴, 크기, 스타일 실시간 편집 지원\n"
                "   - 장문의 멀티라인 텍스트 붙여넣기 시 크래시 없는 바운딩 박스 자동 측정 지원\n\n"
                "3. 선택 영역 삭제 및 Delete 키 동작 고도화:\n"
                "   - Delete 키 입력 시 점선 선택 영역(Marquee)은 유지하면서 내부 이미지/도형만 깔끔하게 삭제\n"
                "   - 투명 선택 토글 OFF 시 서브 컬러(색 2 / 배경색) 유지, 토글 ON 시 투명화 삭제 연동\n"
                "   - 도형 레이어가 활성화된 상태에서도 선택 영역 내부의 이미지 및 도형 정확히 감지 및 삭제\n\n"
                "4. 우클릭 도형 그리기 및 팝업 버그 해결:\n"
                "   - 우클릭 드래그 도형 생성 직후 불필요하게 뜨던 컨텍스트 메뉴 팝업 억제\n"
                "   - 도형 팝업 닫기(바깥 클릭) 시 텍스트 다이얼로그가 돌발 실행되던 버그 완벽 수정\n\n"
                "[ v1.2.2 마이너 패치 안내 ]\n"
                "1. 바로 아래 래스터 레이어로의 병합 로직 개편:\n"
                "   - 도형 병합 시 배경 레이어가 아닌 바로 아래 위치한 래스터 레이어로 정확히 병합\n"
                "   - 중간에 다른 도형 레이어가 있더라도 도형은 건너뛰고 반드시 래스터 레이어에만 안전하게 병합\n"
                "   - 래스터 레이어 패널 및 Ctrl+E 단축키를 통한 '아래 레이어와 병합(Merge Down)' 기능 신규 지원\n\n"
                "[ v1.2.1 마이너 패치 안내 ]\n"
                "1. 도형 자동 래스터라이즈(병합) 버그 수정:\n"
                "   - 도형 수정 후 캔버스 바깥 영역 클릭 시 의도치 않게 레이어로 강제 병합되던 현상 수정\n"
                "   - Enter 키, 더블 클릭, 컨텍스트 메뉴를 통해서만 명시적 병합 지원\n"
                "2. 다크 모드 스크롤바 가시성 개선:\n"
                "   - 소프트 스카이 블루(#60a5fa) 테마 적용으로 가시성 및 조작성 향상\n\n"
                "[ v1.2.0 신규 기능 안내 ]\n"
                "1. 스마트 도구 옵션 바:\n"
                "   - 순서 배지 (단축키 K): 시작 번호 설정 및 숫자/영문 대소문자 스타일 지원\n"
                "   - 모자이크 (단축키 J): 원하는 블록 크기(4~64px)를 자유롭게 조절하여 적용\n"
                "   - 둥근 사각형 (단축키 U): 모서리 곡률(2~64px)을 수치로 정밀하게 조절\n"
                "   - 페인트통 (G): 투명 영역 채우기 허용 범위 (0~100%)\n"
                "   - 마술봉 (W): 유사 색상 선택 허용 범위 (0~255)\n\n"
                "2. 확장 도구 모음:\n"
                "   - 사각형 도구 (단축키 U): 일반 직사각형 / 둥근 직사각형 전환 지원\n"
                "   - 화살표 도구 (단축키 A): 단방향/양방향 직선 및 곡선 화살표 지원\n"
                "   - 버튼 우클릭 또는 길게 누르면 서브 도구 선택 메뉴가 표시됩니다.\n\n"
                "3. 편리한 복사 안내 알림:\n"
                "   - 복사(Ctrl+C), 투명 PNG 복사(Ctrl+Shift+C), 잘라내기(Ctrl+X) 시\n"
                "     화면 상단에 작업을 방해하지 않는 깔끔한 안내 알림이 표시됩니다.\n\n"
                "[ 실행 방법 ]\n"
                "- 'Paint Essential.exe' 파일을 더블 클릭하여 바로 실행할 수 있습니다.\n"
                "- 별도의 설치 과정이 필요 없는 가볍고 빠른 무설치(포터블) 프로그램입니다.\n\n"
                "[ 파일 안내 ]\n"
                "- '_internal' 폴더는 프로그램 구동에 필요한 파일들이 보관된 폴더입니다.\n"
                "  삭제하거나 이동하지 마세요.\n"
            )

        # Create zip archive
        import zipfile
        zip_path = os.path.join("dist", "PaintEssential_v1.3.0_Portable.zip")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(portable_dir):
                for file in files:
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, "dist")
                    zipf.write(full_p, rel_p)

        exe_path = os.path.abspath(os.path.join(portable_dir, "Paint Essential.exe"))
        print(f"\n🎉 Packaging Complete!")
        print(f"👉 Portable Folder: {os.path.abspath(portable_dir)}")
        print(f"👉 Standalone Executable: {exe_path}")
        print(f"👉 Release ZIP: {os.path.abspath(zip_path)}")
    else:
        print("❌ PyInstaller compilation failed.")


if __name__ == "__main__":
    run_tests()
    clean_artifacts()
    package_exe()
