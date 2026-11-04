# eBookToPdf
E-Book PDF 추출 프로그램<br /><br />
제작 과정 : https://eastshine12.tistory.com/55
<br /><br /><br />


# 프로그램 화면
<img src="gui_image_win.png" width="500">
<br /><br /><br />

# 실행파일 위치
eBookToPdf/dist/ebook_to_pdf.exe
<br/><br/><br/>

# 사용법
1. '좌표 위치 클릭' 버튼 클릭 후 캡처할 영역의 좌측상단, 우측하단 좌표를 구한다.
2. 총 페이지 수와 생성할 PDF 이름을 작성한다.
3. 다음 페이지를 넘겨보며 화면이 완전히 랜더링되는 시간을 참고하여 캡처 속도를 조절한다.
4. PDF로 만들기 클릭!
5. 캡처 이미지가 많아지면, PDF 변환 시간이 길어질 수 있으므로 잠시 기다린다.
6. 'PDF 변환 완료!'라는 문구가 뜨면 PDF 생성이 완료된 것이다.
7. PDF 파일은 실행 파일과 같은 경로에 생성된다.
<br /><br /><br />

# 사용 시 유의사항
1. 해당 프로그램은 windows 전용 app이다.
2. 이미지 좌표 영역이 뷰어 영역을 벗어나면 안된다.
3. 반드시 키보드 오른쪽 방향키를 통해 다음 페이지 전환이 되어야 한다.
4. 페이지 수가 많을 경우 PDF 용량이 꽤 되므로 HDD 용량이 여유가 있어야 한다.
5. PDF 재생성 오류 시 프로그램을 재실행한다.
<br /><br /><br />

# v2 (`eBookToPdf_v2.py`, macOS / Windows)
영역을 드래그로 지정하고, 화질 손실 없이 PDF를 만든다.

```bash
pip3 install PySide6 img2pdf
python3 eBookToPdf_v2.py
```

1. '드래그로 지정' 클릭 → 화면이 어두워지면 캡처할 영역을 드래그한다. (취소: ESC)
2. 총 페이지 수와 캡처 간격(0.1~2초)을 정하고 'PDF로 만들기' → 저장 위치를 고른다.
3. 뷰어에 포커스를 주고 캡처가 시작된다. 끝날 때까지 다른 앱을 클릭하지 않는다.
   - macOS: YES24 eBook 앱을 자동으로 앞으로 가져온다.
   - Windows: 기존 버전처럼 캡처 영역 좌상단을 한 번 클릭한다.
4. '중지'를 누르면 그때까지 찍은 페이지로 PDF를 만든다.

유의사항
- macOS: 처음 실행 시 **시스템 설정 > 개인정보 보호 및 보안**에서 터미널 앱에 '화면 기록', '손쉬운 사용' 권한을 허용하고 터미널을 재시작한다.
- macOS: YES24 앱을 전체 화면 모드로 두지 않는다. (영역 지정 막이 다른 Space에 뜬다)
- Windows exe 빌드: `pip install pyinstaller` 후 `pyinstaller --onefile --windowed eBookToPdf_v2.py`
