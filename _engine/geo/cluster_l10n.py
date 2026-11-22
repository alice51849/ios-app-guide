# -*- coding: utf-8 -*-
"""Localized body copy for GEO query clusters.

The autobatch cluster generator (auto_batch_runner.gen_cluster) writes English
bodies with localized navigation labels by default. For the storefront locales
that actually produce App Store impressions we ship fully localized copy here,
so the page is worth clicking and not only worth citing.

Shape:
  PROBLEMS[locale][page_slug] = {
    "title", "desc", "h1", "intro",
    "why": {app_key: sentence},
    "faqs": [(question, answer),...],
  }

Rules for anything added here:
- Only describe features the app really has (art is AI-generated, speech is
 system TTS, nothing is hand-drawn or human-voiced).
- Never quote a price; storefront prices differ. Point at the App Store.
- Keep sentences short: these pages are read on a phone, often via an assistant.
"""

# --- page 1: Wi-Fi connected but no internet ------------------------------
# --- page 2: photo too blurry to read -------------------------------------
# --- page 3: passport photo rejected --------------------------------------
# --- page 4: shared file contains private data ----------------------------
# --- page 5: iPhone storage full ------------------------------------------

PROBLEMS = {
  "ja-JP": {
    "wifi-connected-no-internet": {
      "title": "Wi-Fiは接続済みなのにインターネットに繋がらない — iPhone 2026",
      "desc": "経路・DNS・TCP・TLSのどこで止まっているのかを切り分ける方法。",
      "h1": "iPhoneが「接続済み、インターネットなし」になるとき（2026年）",
      "intro": "電波は立っているのに何も読み込まれない。再起動を繰り返す前に、どの段階で止まっているのか——ローカル経路、DNS、TCP、TLS、それともサーバー側か——を確かめたほうが早く終わります。",
      "why": {
        "wifiaid": "経路・DNS・TCP・TLS・応答時間・電波強度を個別に検査し、最も可能性の高い原因を示します。",
        "cyca": "公共Wi-Fiを信用する前に、その接続から何が見えているのかを確認できます。",
      },
      "faqs": [
        ("アカウント登録は必要ですか？", "不要です。"),
        ("ルーターを自動で直してくれますか？", "いいえ。どこで失敗しているかを示すので、次に何を変えればよいか分かります。"),
      ],
    },
    "photo-too-blurry-to-read": {
      "title": "写真がぼやけて文字が読めない — iPhone 2026",
      "desc": "手ブレや暗所で撮った写真から、読める状態を取り戻す。",
      "h1": "ぼやけた写真の文字を読めるようにする（2026年）",
      "intro": "レシート、ホワイトボード、案内板がぼんやりして読めない。多くの場合、端末内でシャープにするだけで十分です。",
      "why": {
        "unblurry": "端末内で写真のブレを補正し、小さな文字を読める状態に近づけます。",
        "picclear": "そのとき大量に撮った似た写真をまとめて整理できます。",
      },
      "faqs": [
        ("元の写真は変わりますか？", "変わりません。オリジナルはライブラリに残ります。"),
        ("写真はアップロードされますか？", "処理は端末内で行われます。"),
      ],
    },
    "passport-photo-rejected": {
      "title": "パスポート写真が却下された — iPhone 2026",
      "desc": "サイズ・背景・顔の位置を規格どおりに撮り直す。",
      "h1": "パスポート写真が却下されたときに直すところ（2026年）",
      "intro": "却下の理由はたいていサイズ、顔の位置、影、背景の4つです。どれも自宅で直せます。",
      "why": {
        "snapport": "パスポート・ビザ・証明写真のサイズガイド、背景処理、印刷用シートまで対応します。",
        "snapportlite": "同じサイズガイドと編集ツールを無料で使え、一度の購入で書き出しが無制限になります。",
      },
      "faqs": [
        ("どの国の規格に対応していますか？", "書き出す前に、提出先が求めるサイズを選んでください。"),
        ("写真スタジオに行く必要はありますか？", "不要です。無地の壁と昼光で十分です。"),
      ],
    },
    "shared-file-contains-private-data": {
      "title": "共有したい書類に個人情報が入っている — iPhone 2026",
      "desc": "送る前に氏名・口座番号・住所を消す。",
      "h1": "個人情報を漏らさずにファイルを共有する（2026年）",
      "intro": "お絵かきツールで黒く塗るのは墨消しではありません。下の文字はたいてい残ります。きちんと除去してください。",
      "why": {
        "maskmyfile": "ファイル内の個人情報を見つけ、共有前に端末内でマスクします。",
        "scanto": "紙をその場でPDF化するので、元データがサーバーを経由しません。",
      },
      "faqs": [
        ("元のファイルは上書きされますか？", "いいえ。マスク済みのコピーが作られます。"),
        ("ファイルはアップロードされますか？", "いいえ。端末内で処理します。"),
      ],
    },
    "iphone-storage-full": {
      "title": "iPhoneの容量がいっぱい、でも思い出は消したくない — 2026",
      "desc": "重複とゴミを片づけて空き容量をつくる。",
      "h1": "思い出を消さずにiPhoneの容量を空ける（2026年）",
      "intro": "空けられる容量のほとんどは、重複・ブレ写真・スクリーンショットです。惜しい写真ではありません。",
      "why": {
        "picclear": "似た写真やブレた写真をまとめて確認し、一括で整理できます。",
        "scanto": "書類を撮った写真の山を、検索できる1つのPDFに置き換えられます。",
      },
      "faqs": [
        ("勝手に削除されませんか？", "削除前に必ず確認します。"),
        ("iCloudは必要ですか？", "不要です。"),
      ],
    },
  },
  "ko-KR": {
    "wifi-connected-no-internet": {
      "title": "Wi‑Fi는 연결됐는데 인터넷이 안 될 때 — iPhone 2026",
      "desc": "경로·DNS·TCP·TLS 중 어디서 끊기는지 가려내는 방법.",
      "h1": "아이폰 '연결됨, 인터넷 사용 불가' 해결 순서 (2026)",
      "intro": "신호는 멀쩡한데 아무것도 열리지 않습니다. 무작정 재부팅하기 전에 어느 단계에서 막히는지—로컬 경로, DNS, TCP, TLS, 서버—부터 확인하세요.",
      "why": {
        "wifiaid": "경로, DNS, TCP, TLS, 응답 시간, 신호를 각각 검사해 가장 유력한 원인을 알려줍니다.",
        "cyca": "공용 Wi‑Fi를 믿기 전에 그 연결에서 무엇이 노출되는지 확인합니다.",
      },
      "faqs": [
        ("계정이 필요한가요?", "필요 없습니다."),
        ("공유기를 대신 고쳐주나요?", "아니요. 어디서 실패하는지 알려주므로 무엇을 바꿔야 할지 알 수 있습니다."),
      ],
    },
    "photo-too-blurry-to-read": {
      "title": "사진이 흐려서 글자를 못 읽을 때 — iPhone 2026",
      "desc": "흔들리거나 어두운 사진에서 읽을 수 있는 상태를 되찾기.",
      "h1": "흐린 사진의 글자를 읽을 수 있게 만들기 (2026)",
      "intro": "영수증, 화이트보드, 안내판이 뭉개져 읽히지 않습니다. 대개는 기기 안에서 선명하게 만드는 것으로 충분합니다.",
      "why": {
        "unblurry": "기기 안에서 흔들림을 보정해 작은 글자를 다시 읽을 수 있게 합니다.",
        "picclear": "그때 함께 찍힌 비슷한 사진들을 정리합니다.",
      },
      "faqs": [
        ("원본이 바뀌나요?", "아니요. 원본은 라이브러리에 그대로 남습니다."),
        ("사진이 업로드되나요?", "처리는 기기 안에서 이뤄집니다."),
      ],
    },
    "passport-photo-rejected": {
      "title": "여권 사진이 반려됐을 때 — iPhone 2026",
      "desc": "규격 크기와 배경에 맞춰 다시 찍기.",
      "h1": "여권 사진 반려, 무엇을 고쳐야 하나 (2026)",
      "intro": "반려 사유는 대부분 크기, 얼굴 위치, 그림자, 배경 네 가지입니다. 모두 집에서 해결됩니다.",
      "why": {
        "snapport": "여권·비자·신분증 사진의 크기 가이드, 배경 처리, 인쇄용 시트를 제공합니다.",
        "snapportlite": "같은 크기 가이드와 편집 도구를 무료로 쓰고, 한 번 구매하면 내보내기가 무제한입니다.",
      },
      "faqs": [
        ("어느 나라 규격을 지원하나요?", "내보내기 전에 제출 기관이 요구하는 크기를 선택하세요."),
        ("사진관에 가야 하나요?", "아니요. 단색 벽과 자연광이면 충분합니다."),
      ],
    },
    "shared-file-contains-private-data": {
      "title": "공유할 파일에 개인정보가 들어 있을 때 — iPhone 2026",
      "desc": "보내기 전에 이름·계좌번호·주소 지우기.",
      "h1": "개인정보를 흘리지 않고 파일 공유하기 (2026)",
      "intro": "그리기 도구로 검게 칠하는 것은 마스킹이 아닙니다. 아래 글자가 대개 그대로 남습니다. 제대로 제거하세요.",
      "why": {
        "maskmyfile": "파일 속 개인정보를 찾아 공유 전에 기기 안에서 가립니다.",
        "scanto": "종이를 기기에서 바로 PDF로 만들어 원본이 서버를 거치지 않습니다.",
      },
      "faqs": [
        ("원본을 덮어쓰나요?", "아니요. 가려진 사본이 만들어집니다."),
        ("파일이 업로드되나요?", "아니요. 기기 안에서 처리합니다."),
      ],
    },
    "iphone-storage-full": {
      "title": "아이폰 저장 공간 부족, 추억은 지우기 싫을 때 — 2026",
      "desc": "중복과 잡동사니를 정리해 공간 확보하기.",
      "h1": "사진을 지우지 않고 아이폰 용량 늘리기 (2026)",
      "intro": "되찾을 수 있는 공간은 대부분 중복 사진, 흔들린 사진, 스크린샷입니다. 아까운 사진이 아닙니다.",
      "why": {
        "picclear": "비슷한 사진과 흐린 사진을 모아 한 번에 정리합니다.",
        "scanto": "서류를 찍은 사진 더미를 검색 가능한 PDF 하나로 대체합니다.",
      },
      "faqs": [
        ("묻지 않고 삭제하나요?", "아니요. 삭제 전에 확인합니다."),
        ("iCloud가 필요한가요?", "아니요."),
      ],
    },
  },
  "th": {
    "wifi-connected-no-internet": {
      "title": "iPhone ขึ้นว่าเชื่อมต่อ Wi‑Fi แล้วแต่เน็ตไม่ขึ้น — 2026",
      "desc": "ดูว่าติดขัดตรงเส้นทาง DNS TCP หรือ TLS กันแน่",
      "h1": "iPhone เชื่อมต่อแล้วแต่ไม่มีอินเทอร์เน็ต (2026)",
      "intro": "สัญญาณเต็มแต่ไม่มีอะไรโหลดขึ้นมา ก่อนจะรีสตาร์ทซ้ำ ๆ ควรรู้ก่อนว่าติดตรงขั้นไหน — เส้นทางในบ้าน, DNS, TCP, TLS หรือฝั่งเซิร์ฟเวอร์",
      "why": {
        "wifiaid": "ตรวจเส้นทาง DNS TCP TLS เวลาตอบสนอง และความแรงสัญญาณแยกกัน แล้วบอกสาเหตุที่เป็นไปได้มากที่สุด",
        "cyca": "ตรวจว่าการเชื่อมต่อของคุณเปิดเผยอะไรบ้าง ก่อนจะไว้ใจ Wi‑Fi สาธารณะ",
      },
      "faqs": [
        ("ต้องสมัครบัญชีไหม", "ไม่ต้อง"),
        ("แก้เราเตอร์ให้เลยไหม", "ไม่ แต่จะบอกว่าพังตรงไหน เพื่อให้รู้ว่าต้องแก้อะไรต่อ"),
      ],
    },
    "photo-too-blurry-to-read": {
      "title": "รูปเบลอจนอ่านตัวหนังสือไม่ออก — iPhone 2026",
      "desc": "กู้ให้อ่านออกจากรูปที่สั่นหรือถ่ายในที่มืด",
      "h1": "ทำให้ตัวหนังสือในรูปเบลออ่านออก (2026)",
      "intro": "ใบเสร็จ กระดานไวท์บอร์ด หรือป้าย ออกมาเบลอจนอ่านไม่ได้ ส่วนใหญ่แค่เพิ่มความคมชัดในเครื่องก็พอแล้ว",
      "why": {
        "unblurry": "ลดความเบลอในเครื่อง ให้ตัวหนังสือเล็ก ๆ กลับมาอ่านออก",
        "picclear": "เก็บกวาดรูปซ้ำ ๆ ที่ถ่ายรัวไว้ตอนนั้น",
      },
      "faqs": [
        ("รูปต้นฉบับเปลี่ยนไหม", "ไม่ ต้นฉบับยังอยู่ในคลังรูปภาพ"),
        ("อัปโหลดรูปไหม", "ประมวลผลในเครื่อง"),
      ],
    },
    "passport-photo-rejected": {
      "title": "รูปพาสปอร์ตถูกตีกลับ — iPhone 2026",
      "desc": "ถ่ายใหม่ให้ตรงขนาดและพื้นหลังตามระเบียบ",
      "h1": "รูปพาสปอร์ตถูกปฏิเสธ ต้องแก้ตรงไหน (2026)",
      "intro": "สาเหตุที่ถูกตีกลับมักเป็นขนาด ตำแหน่งศีรษะ เงา และพื้นหลัง ทั้งสี่อย่างแก้เองที่บ้านได้",
      "why": {
        "snapport": "มีไกด์ขนาด เครื่องมือจัดการพื้นหลัง และแผ่นพร้อมพิมพ์ สำหรับรูปพาสปอร์ต วีซ่า และบัตรประจำตัว",
        "snapportlite": "ไกด์ขนาดและเครื่องมือแก้ไขเดียวกันใช้ได้ฟรี ซื้อครั้งเดียวเพื่อส่งออกได้ไม่จำกัด",
      },
      "faqs": [
        ("รองรับระเบียบประเทศไหน", "เลือกขนาดที่หน่วยงานของคุณกำหนดก่อนส่งออก"),
        ("ต้องไปร้านถ่ายรูปไหม", "ไม่ต้อง ผนังสีเรียบกับแสงธรรมชาติก็พอ"),
      ],
    },
    "shared-file-contains-private-data": {
      "title": "ต้องส่งไฟล์ที่มีข้อมูลส่วนตัวอยู่ — iPhone 2026",
      "desc": "ลบชื่อ เลขบัญชี และที่อยู่ก่อนส่ง",
      "h1": "แชร์ไฟล์โดยไม่หลุดข้อมูลส่วนตัว (2026)",
      "intro": "การใช้ปากกาป้ายดำทับไม่ใช่การลบข้อมูล ตัวหนังสือข้างใต้มักยังอยู่ ต้องลบให้จริง",
      "why": {
        "maskmyfile": "หาข้อมูลส่วนตัวในไฟล์แล้วปิดบังในเครื่องก่อนที่คุณจะแชร์",
        "scanto": "สแกนกระดาษเป็น PDF ในเครื่อง ต้นฉบับจึงไม่ผ่านเซิร์ฟเวอร์",
      },
      "faqs": [
        ("ทับไฟล์เดิมไหม", "ไม่ จะได้สำเนาที่ปิดบังแล้ว"),
        ("อัปโหลดไฟล์ไหม", "ไม่ ทำงานในเครื่อง"),
      ],
    },
    "iphone-storage-full": {
      "title": "พื้นที่ iPhone เต็ม แต่ไม่อยากลบความทรงจำ — 2026",
      "desc": "เพิ่มพื้นที่ด้วยการเก็บกวาดรูปซ้ำและของรก",
      "h1": "พื้นที่ iPhone เต็ม ทำอย่างไรไม่ต้องลบรูปสำคัญ (2026)",
      "intro": "พื้นที่ที่ได้คืนส่วนใหญ่มาจากรูปซ้ำ รูปเบลอ และภาพหน้าจอ ไม่ใช่รูปที่คุณเสียดาย",
      "why": {
        "picclear": "ดูรูปที่เกือบซ้ำและรูปเบลอ แล้วเคลียร์ทีละชุด",
        "scanto": "แทนกองรูปถ่ายเอกสารด้วย PDF ที่ค้นหาได้ไฟล์เดียว",
      },
      "faqs": [
        ("ลบเองโดยไม่ถามไหม", "ไม่ คุณต้องยืนยันก่อนเสมอ"),
        ("ต้องใช้ iCloud ไหม", "ไม่ต้อง"),
      ],
    },
  },
  "vi": {
    "wifi-connected-no-internet": {
      "title": "iPhone báo đã kết nối Wi‑Fi nhưng không vào được mạng — 2026",
      "desc": "Xác định mắt xích nào thực sự hỏng: đường truyền, DNS, TCP hay TLS.",
      "h1": "iPhone đã kết nối nhưng không có Internet (2026)",
      "intro": "Sóng đầy nhưng không tải được gì. Trước khi khởi động lại lần thứ năm, hãy xác định bước nào đang hỏng — đường truyền nội bộ, DNS, TCP, TLS hay phía máy chủ.",
      "why": {
        "wifiaid": "Kiểm tra riêng đường truyền, DNS, TCP, TLS, độ trễ và cường độ sóng rồi chỉ ra nguyên nhân khả dĩ nhất.",
        "cyca": "Kiểm tra kết nối của bạn đang để lộ những gì trước khi tin vào Wi‑Fi công cộng.",
      },
      "faqs": [
        ("Có cần tài khoản không?", "Không."),
        ("Ứng dụng có sửa router giúp không?", "Không. Nó cho biết chỗ hỏng để bạn biết cần thay đổi gì."),
      ],
    },
    "photo-too-blurry-to-read": {
      "title": "Ảnh quá mờ, không đọc được chữ — iPhone 2026",
      "desc": "Lấy lại bản đọc được từ ảnh rung hoặc thiếu sáng.",
      "h1": "Làm rõ chữ trong ảnh bị mờ (2026)",
      "intro": "Hoá đơn, bảng trắng hay biển chỉ dẫn chụp ra bị nhoè. Thường chỉ cần làm nét ngay trên máy là đủ.",
      "why": {
        "unblurry": "Giảm nhoè ngay trên máy để chữ nhỏ đọc được trở lại.",
        "picclear": "Dọn luôn loạt ảnh gần giống nhau chụp cùng lúc đó.",
      },
      "faqs": [
        ("Ảnh gốc có bị đổi không?", "Không. Ảnh gốc vẫn nằm trong thư viện."),
        ("Ảnh có bị tải lên không?", "Xử lý diễn ra trên máy."),
      ],
    },
    "passport-photo-rejected": {
      "title": "Ảnh hộ chiếu bị từ chối — iPhone 2026",
      "desc": "Chụp lại đúng kích thước và nền theo quy định.",
      "h1": "Ảnh hộ chiếu bị trả lại — cần sửa gì (2026)",
      "intro": "Lý do bị trả lại thường là kích thước, vị trí đầu, bóng đổ và nền. Cả bốn đều xử lý được tại nhà.",
      "why": {
        "snapport": "Hướng dẫn kích thước, công cụ xử lý nền và bản in sẵn cho ảnh hộ chiếu, visa và giấy tờ tuỳ thân.",
        "snapportlite": "Cùng hướng dẫn kích thước và công cụ chỉnh sửa, dùng miễn phí; mua một lần để xuất ảnh không giới hạn.",
      },
      "faqs": [
        ("Hỗ trợ quy định nước nào?", "Chọn kích thước cơ quan yêu cầu trước khi xuất ảnh."),
        ("Có cần ra tiệm ảnh không?", "Không. Một bức tường trơn và ánh sáng ban ngày là đủ."),
      ],
    },
    "shared-file-contains-private-data": {
      "title": "Cần gửi tệp nhưng trong đó có dữ liệu riêng tư — iPhone 2026",
      "desc": "Xoá tên, số tài khoản và địa chỉ trước khi gửi.",
      "h1": "Chia sẻ tệp mà không lộ dữ liệu riêng tư (2026)",
      "intro": "Bôi đen bằng công cụ vẽ không phải là che dữ liệu — chữ bên dưới thường vẫn còn. Hãy loại bỏ đúng cách.",
      "why": {
        "maskmyfile": "Tìm dữ liệu riêng tư trong tệp và che ngay trên máy trước khi bạn chia sẻ.",
        "scanto": "Quét giấy thành PDF ngay trên máy, nên bản gốc không đi qua máy chủ.",
      },
      "faqs": [
        ("Tệp gốc có bị ghi đè không?", "Không, một bản đã che sẽ được tạo ra."),
        ("Tệp có bị tải lên không?", "Không. Mọi xử lý ở trên máy."),
      ],
    },
    "iphone-storage-full": {
      "title": "iPhone đầy bộ nhớ mà không muốn xoá kỷ niệm — 2026",
      "desc": "Giải phóng dung lượng bằng cách dọn ảnh trùng và ảnh rác.",
      "h1": "iPhone hết dung lượng (2026)",
      "intro": "Phần lớn dung lượng lấy lại được nằm ở ảnh trùng, ảnh rung và ảnh chụp màn hình — không phải những tấm bạn tiếc.",
      "why": {
        "picclear": "Xem lại ảnh gần trùng và ảnh mờ rồi dọn theo lô.",
        "scanto": "Thay cả chồng ảnh chụp giấy tờ bằng một tệp PDF tìm kiếm được.",
      },
      "faqs": [
        ("Có tự xoá không hỏi không?", "Không. Bạn xác nhận trước khi xoá."),
        ("Có cần iCloud không?", "Không."),
      ],
    },
  },
  "pt-BR": {
    "wifi-connected-no-internet": {
      "title": "iPhone diz que o Wi‑Fi está conectado, mas não tem internet — 2026",
      "desc": "Descubra qual elo está realmente quebrado: rota, DNS, TCP ou TLS.",
      "h1": "Wi‑Fi conectado, sem internet no iPhone (2026)",
      "intro": "O sinal está cheio e nada carrega. Antes de reiniciar pela quinta vez, vale saber em que etapa a conexão falha — rota local, DNS, TCP, TLS ou o servidor.",
      "why": {
        "wifiaid": "Testa rota, DNS, TCP, TLS, tempo de resposta e sinal separadamente e aponta a causa mais provável.",
        "cyca": "Mostra o que a sua conexão expõe antes de você confiar em um Wi‑Fi público.",
      },
      "faqs": [
        ("Precisa de conta?", "Não."),
        ("Ele conserta o roteador?", "Não. Ele mostra onde a falha está, para você saber o que mudar."),
      ],
    },
    "photo-too-blurry-to-read": {
      "title": "Foto borrada demais para ler o texto — iPhone 2026",
      "desc": "Recupere uma cópia legível de uma foto tremida ou escura.",
      "h1": "Foto borrada demais para ler (2026)",
      "intro": "Um recibo, um quadro branco ou uma placa saiu sem nitidez e o texto ficou ilegível. Nitidez no próprio aparelho costuma resolver.",
      "why": {
        "unblurry": "Reduz o borrão no próprio aparelho para que o texto pequeno volte a ser legível.",
        "picclear": "Limpa as fotos quase iguais que sobraram da mesma sequência.",
      },
      "faqs": [
        ("A foto original muda?", "Não. A original continua na sua biblioteca."),
        ("A foto é enviada para algum servidor?", "O processamento acontece no aparelho."),
      ],
    },
    "passport-photo-rejected": {
      "title": "Minha foto de passaporte foi recusada — iPhone 2026",
      "desc": "Refaça a foto no tamanho e no fundo exigidos.",
      "h1": "Foto de passaporte recusada — o que corrigir (2026)",
      "intro": "As recusas quase sempre são por tamanho, posição da cabeça, sombras ou fundo. Dá para resolver os quatro em casa.",
      "why": {
        "snapport": "Guia de enquadramento, ferramentas de fundo e folha pronta para impressão de fotos de passaporte, visto e documentos.",
        "snapportlite": "O mesmo guia de enquadramento e as ferramentas de edição, grátis; uma compra única libera exportações ilimitadas.",
      },
      "faqs": [
        ("Serve para qual país?", "Escolha o tamanho exigido pelo órgão antes de exportar."),
        ("Preciso de estúdio?", "Não. Uma parede lisa e luz do dia bastam."),
      ],
    },
    "shared-file-contains-private-data": {
      "title": "Preciso enviar um arquivo com dados pessoais — iPhone 2026",
      "desc": "Remova nomes, números e endereços antes de compartilhar.",
      "h1": "Compartilhar arquivos sem vazar dados pessoais (2026)",
      "intro": "Pintar por cima com uma ferramenta de desenho não é tarjar — o texto costuma continuar embaixo. Remova de verdade.",
      "why": {
        "maskmyfile": "Encontra dados pessoais no arquivo e os oculta no aparelho antes de você compartilhar.",
        "scanto": "Digitaliza papel em PDF localmente, então a origem nunca passa por um servidor.",
      },
      "faqs": [
        ("O arquivo original é sobrescrito?", "Não, é gerada uma cópia já tarjada."),
        ("O arquivo é enviado para a nuvem?", "Não. O trabalho é feito no aparelho."),
      ],
    },
    "iphone-storage-full": {
      "title": "Armazenamento do iPhone cheio sem apagar memórias — 2026",
      "desc": "Libere espaço tirando duplicadas e entulho, não as fotos que importam.",
      "h1": "Armazenamento do iPhone cheio (2026)",
      "intro": "A maior parte do espaço recuperável está em duplicadas, fotos tremidas e capturas de tela — não nas fotos de que você sentiria falta.",
      "why": {
        "picclear": "Revise quase duplicadas e fotos borradas e limpe em lote.",
        "scanto": "Troque pilhas de fotos de documentos por um único PDF pesquisável.",
      },
      "faqs": [
        ("Ele apaga sem perguntar?", "Não. Você confirma antes de qualquer remoção."),
        ("Precisa de iCloud?", "Não."),
      ],
    },
  },
  "de-DE": {
    "wifi-connected-no-internet": {
      "title": "iPhone sagt WLAN verbunden, aber kein Internet — 2026",
      "desc": "Finden Sie heraus, welches Glied tatsächlich bricht: Route, DNS, TCP oder TLS.",
      "h1": "WLAN verbunden, kein Internet am iPhone (2026)",
      "intro": "Volle Balken, aber nichts lädt. Bevor Sie zum fünften Mal neu starten: Klären Sie, welcher Schritt scheitert — lokale Route, DNS, TCP, TLS oder der Server.",
      "why": {
        "wifiaid": "Prüft Route, DNS, TCP, TLS, Antwortzeiten und Signal einzeln und nennt die wahrscheinlichste Ursache.",
        "cyca": "Zeigt, was Ihre Verbindung preisgibt, bevor Sie einem öffentlichen WLAN vertrauen.",
      },
      "faqs": [
        ("Ist ein Konto nötig?", "Nein."),
        ("Repariert die App den Router?", "Nein. Sie zeigt, wo es scheitert, damit Sie wissen, was zu ändern ist."),
      ],
    },
    "photo-too-blurry-to-read": {
      "title": "Foto zu unscharf, um den Text zu lesen — iPhone 2026",
      "desc": "Aus einer verwackelten Aufnahme wieder etwas Lesbares machen.",
      "h1": "Unscharfes Foto wieder lesbar machen (2026)",
      "intro": "Quittung, Whiteboard oder Schild sind weich geworden und der Text ist unlesbar. Nachschärfen auf dem Gerät reicht meist aus.",
      "why": {
        "unblurry": "Reduziert Unschärfe auf dem Gerät, damit kleine Schrift wieder lesbar wird.",
        "picclear": "Räumt die fast identischen Aufnahmen derselben Serie auf.",
      },
      "faqs": [
        ("Wird das Original verändert?", "Nein. Das Original bleibt in der Mediathek."),
        ("Wird mein Foto hochgeladen?", "Die Verarbeitung findet auf dem Gerät statt."),
      ],
    },
    "passport-photo-rejected": {
      "title": "Mein Passfoto wurde abgelehnt — iPhone 2026",
      "desc": "Biometrisches Foto in korrekter Größe und mit passendem Hintergrund neu aufnehmen.",
      "h1": "Passfoto abgelehnt — was zu korrigieren ist (2026)",
      "intro": "Ablehnungen liegen fast immer an Größe, Kopfposition, Schatten oder Hintergrund. Alle vier lassen sich zu Hause beheben.",
      "why": {
        "snapport": "Größenführung, Hintergrundwerkzeuge und druckfertiger Bogen für Pass-, Visa- und Ausweisfotos.",
        "snapportlite": "Dieselbe Größenführung und dieselben Bearbeitungswerkzeuge gratis; ein Einmalkauf schaltet unbegrenzte Exporte frei.",
      },
      "faqs": [
        ("Welche Ländervorgaben?", "Wählen Sie vor dem Export die von Ihrer Behörde geforderte Größe."),
        ("Brauche ich ein Fotostudio?", "Nein. Eine glatte Wand und Tageslicht genügen."),
      ],
    },
    "shared-file-contains-private-data": {
      "title": "Ich muss eine Datei teilen, die private Daten enthält — iPhone 2026",
      "desc": "Namen, Nummern und Adressen vor dem Senden entfernen.",
      "h1": "Dateien teilen, ohne private Daten preiszugeben (2026)",
      "intro": "Mit einem Zeichenwerkzeug schwärzen ist kein Schwärzen — der Text bleibt meist darunter erhalten. Entfernen Sie ihn richtig.",
      "why": {
        "maskmyfile": "Findet private Angaben in einer Datei und maskiert sie auf dem Gerät, bevor Sie teilen.",
        "scanto": "Scannt Papier lokal zu PDF, die Quelle erreicht also nie einen Server.",
      },
      "faqs": [
        ("Wird das Original überschrieben?", "Nein, es entsteht eine maskierte Kopie."),
        ("Wird die Datei hochgeladen?", "Nein. Die Arbeit passiert auf dem Gerät."),
      ],
    },
    "iphone-storage-full": {
      "title": "iPhone-Speicher voll, ohne Erinnerungen zu löschen — 2026",
      "desc": "Platz schaffen durch Duplikate und Ballast statt durch Fotos, die zählen.",
      "h1": "iPhone-Speicher voll (2026)",
      "intro": "Der meiste zurückgewinnbare Platz steckt in Duplikaten, verwackelten Aufnahmen und Screenshots — nicht in den Fotos, die Sie vermissen würden.",
      "why": {
        "picclear": "Fast-Duplikate und unscharfe Aufnahmen durchsehen und stapelweise entfernen.",
        "scanto": "Stapel von Dokumentfotos durch ein einziges durchsuchbares PDF ersetzen.",
      },
      "faqs": [
        ("Löscht die App ungefragt?", "Nein. Sie bestätigen vor jeder Entfernung."),
        ("Wird iCloud benötigt?", "Nein."),
      ],
    },
  },
  "ms": {
    "wifi-connected-no-internet": {
      "title": "iPhone kata Wi‑Fi disambung tetapi tiada internet — 2026",
      "desc": "Kenal pasti bahagian mana yang sebenarnya gagal: laluan, DNS, TCP atau TLS.",
      "h1": "Wi‑Fi disambung, tiada internet pada iPhone (2026)",
      "intro": "Bar penuh tetapi tiada apa yang dimuat. Sebelum but semula kali kelima, tentukan dulu langkah mana yang gagal — laluan setempat, DNS, TCP, TLS atau pelayan.",
      "why": {
        "wifiaid": "Menguji laluan, DNS, TCP, TLS, masa tindak balas dan isyarat secara berasingan lalu menunjukkan punca paling berkemungkinan.",
        "cyca": "Menyemak apa yang didedahkan oleh sambungan anda sebelum anda percaya Wi‑Fi awam.",
      },
      "faqs": [
        ("Perlukah akaun?", "Tidak."),
        ("Adakah ia membaiki penghala?", "Tidak. Ia menunjukkan di mana kegagalan berlaku supaya anda tahu apa yang perlu diubah."),
      ],
    },
    "photo-too-blurry-to-read": {
      "title": "Gambar terlalu kabur untuk baca teks — iPhone 2026",
      "desc": "Dapatkan semula salinan yang boleh dibaca daripada gambar goyang.",
      "h1": "Gambar terlalu kabur untuk dibaca (2026)",
      "intro": "Resit, papan putih atau papan tanda keluar lembut dan teksnya tidak terbaca. Menajamkan pada peranti biasanya sudah memadai.",
      "why": {
        "unblurry": "Mengurangkan kabur pada peranti supaya teks kecil boleh dibaca semula.",
        "picclear": "Membersihkan gambar hampir serupa yang tertinggal daripada rentetan sama.",
      },
      "faqs": [
        ("Adakah gambar asal berubah?", "Tidak. Gambar asal kekal dalam pustaka anda."),
        ("Adakah gambar dimuat naik?", "Pemprosesan berlaku pada peranti."),
      ],
    },
    "passport-photo-rejected": {
      "title": "Gambar pasport saya ditolak — iPhone 2026",
      "desc": "Ambil semula gambar mengikut saiz dan latar rasmi.",
      "h1": "Gambar pasport ditolak — apa yang perlu dibetulkan (2026)",
      "intro": "Penolakan biasanya kerana saiz, kedudukan kepala, bayang atau latar belakang. Keempat-empatnya boleh dibetulkan di rumah.",
      "why": {
        "snapport": "Panduan saiz, alat latar belakang dan helaian sedia cetak untuk gambar pasport, visa dan kad pengenalan.",
        "snapportlite": "Panduan saiz dan alat suntingan yang sama, percuma; satu pembelian membuka eksport tanpa had.",
      },
      "faqs": [
        ("Spesifikasi negara mana?", "Pilih saiz yang diperlukan pihak berkuasa anda sebelum mengeksport."),
        ("Perlukah studio gambar?", "Tidak. Dinding kosong dan cahaya siang sudah cukup."),
      ],
    },
    "shared-file-contains-private-data": {
      "title": "Saya perlu kongsi fail yang mengandungi data peribadi — iPhone 2026",
      "desc": "Buang nama, nombor dan alamat sebelum menghantar.",
      "h1": "Kongsi fail tanpa membocorkan data peribadi (2026)",
      "intro": "Menghitamkan dengan alat lukisan bukan penyuntingan sebenar — teks di bawah selalunya masih ada. Buang dengan betul.",
      "why": {
        "maskmyfile": "Mencari butiran peribadi dalam fail dan menutupnya pada peranti sebelum anda berkongsi.",
        "scanto": "Mengimbas kertas ke PDF secara setempat, jadi sumbernya tidak pernah menyentuh pelayan.",
      },
      "faqs": [
        ("Adakah fail asal ditulis ganti?", "Tidak, satu salinan bertopeng dihasilkan."),
        ("Adakah fail dimuat naik?", "Tidak. Kerja dilakukan pada peranti."),
      ],
    },
    "iphone-storage-full": {
      "title": "Storan iPhone penuh tanpa memadam kenangan — 2026",
      "desc": "Bebaskan ruang dengan membuang pendua dan sampah, bukan gambar yang bermakna.",
      "h1": "Storan iPhone penuh (2026)",
      "intro": "Kebanyakan ruang yang boleh dituntut semula ada pada pendua, gambar kabur dan tangkapan skrin — bukan gambar yang anda rindui.",
      "why": {
        "picclear": "Semak gambar hampir serupa dan gambar kabur, kemudian bersihkan secara berkelompok.",
        "scanto": "Ganti timbunan gambar dokumen dengan satu PDF yang boleh dicari.",
      },
      "faqs": [
        ("Adakah ia memadam tanpa bertanya?", "Tidak. Anda mengesahkan sebelum apa-apa dibuang."),
        ("Perlukah iCloud?", "Tidak."),
      ],
    },
  },
  "zh-Hant": {
    "wifi-connected-no-internet": {
      "title": "iPhone 顯示已連線 Wi‑Fi 卻不能上網 — 2026",
      "desc": "分辨到底是路徑、DNS、TCP 還是 TLS 出問題。",
      "h1": "iPhone 已連線但沒有網路(2026)",
      "intro": "訊號滿格卻什麼都載不出來。與其重開機第五次,不如先確認是哪一段失敗:本地路徑、DNS、TCP、TLS,還是伺服器端。",
      "why": {
        "wifiaid": "分別檢查路徑、DNS、TCP、TLS、回應時間與訊號強度,指出最可能的原因。",
        "cyca": "在你信任公共 Wi‑Fi 之前,先看看這個連線會暴露什麼。",
      },
      "faqs": [
        ("需要註冊帳號嗎?", "不需要。"),
        ("它會幫我修好路由器嗎?", "不會。它告訴你哪一段失敗,你才知道要改什麼。"),
      ],
    },
    "photo-too-blurry-to-read": {
      "title": "照片太模糊看不清楚字 — iPhone 2026",
      "desc": "把手震或昏暗環境拍到的照片救回可讀狀態。",
      "h1": "照片太模糊,把字救回來(2026)",
      "intro": "收據、白板或指示牌拍糊了,字完全看不清。多數情況下,在裝置上銳化就夠了。",
      "why": {
        "unblurry": "在裝置上修正模糊,讓小字重新變得可讀。",
        "picclear": "順手清掉當時連拍留下的一堆相似照片。",
      },
      "faqs": [
        ("原始照片會被改動嗎?", "不會,原始檔留在你的照片圖庫。"),
        ("照片會被上傳嗎?", "處理在裝置上進行。"),
      ],
    },
    "passport-photo-rejected": {
      "title": "護照照片被退件 — iPhone 2026",
      "desc": "依官方規格重拍尺寸與背景。",
      "h1": "護照照片被退,該修哪裡(2026)",
      "intro": "被退件多半是尺寸、頭部位置、陰影或背景這四項。四項都能在家自己處理。",
      "why": {
        "snapport": "護照、簽證與證件照的尺寸導引、背景處理,以及可直接列印的排版。",
        "snapportlite": "同一套尺寸導引與編輯工具免費使用,一次購買解鎖無限匯出。",
      },
      "faqs": [
        ("支援哪個國家的規格?", "匯出前先選擇受理單位要求的尺寸。"),
        ("需要去照相館嗎?", "不需要,一面素色牆加自然光就夠了。"),
      ],
    },
    "shared-file-contains-private-data": {
      "title": "要傳的檔案裡有個資 — iPhone 2026",
      "desc": "送出前先把姓名、帳號、地址處理掉。",
      "h1": "分享檔案又不外洩個資(2026)",
      "intro": "用畫筆塗黑不等於遮蔽,底下的文字通常還在。要真的移除才算數。",
      "why": {
        "maskmyfile": "找出檔案裡的個資,在你分享之前於裝置上遮蔽。",
        "scanto": "在本機把紙本掃成 PDF,來源檔完全不經過伺服器。",
      },
      "faqs": [
        ("會覆蓋原始檔嗎?", "不會,會另外產生一份已遮蔽的副本。"),
        ("檔案會被上傳嗎?", "不會,處理都在裝置上完成。"),
      ],
    },
    "iphone-storage-full": {
      "title": "iPhone 容量滿了又捨不得刪回憶 — 2026",
      "desc": "靠清重複與雜物釋出空間,而不是刪掉在意的照片。",
      "h1": "iPhone 容量已滿(2026)",
      "intro": "真正能清出來的空間,大多是重複照、手震廢片和截圖,而不是你會捨不得的那些。",
      "why": {
        "picclear": "檢視近乎重複與模糊的照片,分批清理。",
        "scanto": "把一整疊拍文件的照片,換成一份可搜尋的 PDF。",
      },
      "faqs": [
        ("會不問就刪掉嗎?", "不會,刪除前一定先讓你確認。"),
        ("需要 iCloud 嗎?", "不需要。"),
      ],
    },
  },
  "es-ES": {
    "wifi-connected-no-internet": {
      "title": "El iPhone dice que el Wi‑Fi está conectado pero no hay internet — 2026",
      "desc": "Averigua qué eslabón falla de verdad: ruta, DNS, TCP o TLS.",
      "h1": "Wi‑Fi conectado, sin internet en el iPhone (2026)",
      "intro": "La cobertura está llena y no carga nada. Antes de reiniciar por quinta vez, conviene saber qué paso falla: ruta local, DNS, TCP, TLS o el servidor.",
      "why": {
        "wifiaid": "Comprueba ruta, DNS, TCP, TLS, tiempos de respuesta y señal por separado y señala la causa más probable.",
        "cyca": "Muestra qué expone tu conexión antes de que confíes en un Wi‑Fi público.",
      },
      "faqs": [
        ("¿Hace falta una cuenta?", "No."),
        ("¿Me arregla el router?", "No. Te dice dónde está el fallo para que sepas qué cambiar."),
      ],
    },
    "photo-too-blurry-to-read": {
      "title": "Foto demasiado borrosa para leer el texto — iPhone 2026",
      "desc": "Recupera una copia legible de una foto movida o con poca luz.",
      "h1": "Foto demasiado borrosa para leerla (2026)",
      "intro": "Un recibo, una pizarra o un cartel han salido blandos y el texto no se lee. Enfocar en el propio dispositivo suele bastar.",
      "why": {
        "unblurry": "Reduce el desenfoque en el dispositivo para que el texto pequeño vuelva a leerse.",
        "picclear": "Limpia las fotos casi idénticas que quedaron de la misma ráfaga.",
      },
      "faqs": [
        ("¿Cambia el original?", "No. El original sigue en tu fototeca."),
        ("¿Sube mi foto a algún servidor?", "El procesado ocurre en el dispositivo."),
      ],
    },
    "passport-photo-rejected": {
      "title": "Me han rechazado la foto de pasaporte — iPhone 2026",
      "desc": "Repite la foto con el tamaño y el fondo que exige la normativa.",
      "h1": "Foto de pasaporte rechazada: qué corregir (2026)",
      "intro": "Los rechazos casi siempre son por tamaño, posición de la cabeza, sombras o fondo. Los cuatro se arreglan en casa.",
      "why": {
        "snapport": "Guía de encuadre, herramientas de fondo y hoja lista para imprimir para fotos de pasaporte, visado y DNI.",
        "snapportlite": "La misma guía de encuadre y las herramientas de edición, gratis; una compra única desbloquea exportaciones ilimitadas.",
      },
      "faqs": [
        ("¿Qué normativa de país?", "Elige el tamaño que exige tu organismo antes de exportar."),
        ("¿Necesito un estudio?", "No. Una pared lisa y luz de día bastan."),
      ],
    },
    "shared-file-contains-private-data": {
      "title": "Tengo que compartir un archivo con datos privados — iPhone 2026",
      "desc": "Elimina nombres, números y direcciones antes de enviarlo.",
      "h1": "Compartir archivos sin filtrar datos privados (2026)",
      "intro": "Tachar con una herramienta de dibujo no es censurar: el texto suele seguir debajo. Elimínalo de verdad.",
      "why": {
        "maskmyfile": "Encuentra datos privados en el archivo y los oculta en el dispositivo antes de compartirlo.",
        "scanto": "Escanea papel a PDF en local, así el origen nunca pasa por un servidor.",
      },
      "faqs": [
        ("¿Se sobrescribe el original?", "No, se genera una copia ya oculta."),
        ("¿Se sube el archivo?", "No. El trabajo ocurre en el dispositivo."),
      ],
    },
    "iphone-storage-full": {
      "title": "Almacenamiento del iPhone lleno sin borrar recuerdos — 2026",
      "desc": "Libera espacio quitando duplicados y ruido, no las fotos que importan.",
      "h1": "Almacenamiento del iPhone lleno (2026)",
      "intro": "Casi todo el espacio recuperable está en duplicados, fotos movidas y capturas de pantalla, no en las fotos que echarías de menos.",
      "why": {
        "picclear": "Revisa casi duplicados y fotos borrosas y límpialos por lotes.",
        "scanto": "Sustituye montones de fotos de documentos por un único PDF con búsqueda.",
      },
      "faqs": [
        ("¿Borra sin preguntar?", "No. Confirmas antes de eliminar nada."),
        ("¿Necesita iCloud?", "No."),
      ],
    },
  },
  "fr-FR": {
    "wifi-connected-no-internet": {
      "title": "L'iPhone indique Wi‑Fi connecté mais pas d'Internet — 2026",
      "desc": "Identifiez le maillon réellement en cause : route, DNS, TCP ou TLS.",
      "h1": "Wi‑Fi connecté, pas d'Internet sur iPhone (2026)",
      "intro": "Le signal est plein et rien ne charge. Avant de redémarrer une cinquième fois, déterminez l'étape qui échoue : route locale, DNS, TCP, TLS ou le serveur.",
      "why": {
        "wifiaid": "Teste séparément la route, le DNS, TCP, TLS, les temps de réponse et le signal, puis désigne la cause la plus probable.",
        "cyca": "Montre ce que votre connexion expose avant que vous ne fassiez confiance à un Wi‑Fi public.",
      },
      "faqs": [
        ("Faut-il un compte ?", "Non."),
        ("Est-ce que ça répare la box ?", "Non. L'app indique où ça casse, pour que vous sachiez quoi changer."),
      ],
    },
    "photo-too-blurry-to-read": {
      "title": "Photo trop floue pour lire le texte — iPhone 2026",
      "desc": "Récupérez une version lisible d'une photo bougée ou sombre.",
      "h1": "Photo trop floue pour être lue (2026)",
      "intro": "Un reçu, un tableau blanc ou un panneau est sorti mou et le texte est illisible. Un renforcement de netteté sur l'appareil suffit souvent.",
      "why": {
        "unblurry": "Réduit le flou sur l'appareil pour que les petits caractères redeviennent lisibles.",
        "picclear": "Nettoie les photos presque identiques laissées par la même rafale.",
      },
      "faqs": [
        ("L'original est-il modifié ?", "Non. L'original reste dans votre photothèque."),
        ("Ma photo est-elle envoyée ailleurs ?", "Le traitement a lieu sur l'appareil."),
      ],
    },
    "passport-photo-rejected": {
      "title": "Ma photo de passeport a été refusée — iPhone 2026",
      "desc": "Refaites la photo au bon format et sur le bon fond.",
      "h1": "Photo de passeport refusée : que corriger (2026)",
      "intro": "Les refus viennent presque toujours du format, de la position de la tête, des ombres ou du fond. Les quatre se corrigent chez soi.",
      "why": {
        "snapport": "Guide de cadrage, outils de fond et planche prête à imprimer pour photos de passeport, de visa et d'identité.",
        "snapportlite": "Le même guide de cadrage et les mêmes outils d’édition, gratuits ; un achat unique débloque les exports illimités.",
      },
      "faqs": [
        ("Quelles normes nationales ?", "Choisissez le format exigé par votre administration avant d'exporter."),
        ("Faut-il un photographe ?", "Non. Un mur uni et la lumière du jour suffisent."),
      ],
    },
    "shared-file-contains-private-data": {
      "title": "Je dois partager un fichier contenant des données privées — iPhone 2026",
      "desc": "Retirez noms, numéros et adresses avant l'envoi.",
      "h1": "Partager un fichier sans laisser fuir des données privées (2026)",
      "intro": "Noircir avec un outil de dessin n'est pas un caviardage : le texte reste souvent dessous. Supprimez-le vraiment.",
      "why": {
        "maskmyfile": "Repère les données privées d'un fichier et les masque sur l'appareil avant le partage.",
        "scanto": "Numérise le papier en PDF en local : la source ne passe jamais par un serveur.",
      },
      "faqs": [
        ("L'original est-il écrasé ?", "Non, une copie masquée est produite."),
        ("Le fichier est-il envoyé en ligne ?", "Non. Tout se passe sur l'appareil."),
      ],
    },
    "iphone-storage-full": {
      "title": "Stockage iPhone plein sans supprimer de souvenirs — 2026",
      "desc": "Libérez de l'espace en retirant doublons et fouillis, pas les photos qui comptent.",
      "h1": "Stockage iPhone plein (2026)",
      "intro": "L'essentiel de l'espace récupérable se trouve dans les doublons, les photos bougées et les captures d'écran, pas dans les photos qui vous manqueraient.",
      "why": {
        "picclear": "Passez en revue quasi-doublons et photos floues, puis nettoyez par lots.",
        "scanto": "Remplacez des piles de photos de documents par un seul PDF consultable.",
      },
      "faqs": [
        ("L'app supprime-t-elle sans demander ?", "Non. Vous confirmez avant toute suppression."),
        ("Faut-il iCloud ?", "Non."),
      ],
    },
  },
}


# Pricing wording per purchase_model, localized. Keys match
# auto_batch_runner.PRICING_LINE; missing locales fall back to English.
PRICING = {
  "ja-JP": {
    "paid_upfront": "買い切り。サブスクリプションなし。",
    "free_with_lifetime_unlock": "無料でダウンロード、買い切りで全機能を解放。",
    "free": "無料。",
    "flexible": "買い切りの解放オプションあり。サブスクリプションは任意。",
  },
  "ko-KR": {
    "paid_upfront": "한 번 결제, 구독 없음.",
    "free_with_lifetime_unlock": "무료 다운로드, 한 번 결제로 잠금 해제.",
    "free": "무료.",
    "flexible": "한 번 결제로 해제 가능. 구독은 선택 사항.",
  },
  "th": {
    "paid_upfront": "จ่ายครั้งเดียว ไม่มีค่าบริการรายเดือน",
    "free_with_lifetime_unlock": "ดาวน์โหลดฟรี ปลดล็อกด้วยการจ่ายครั้งเดียว",
    "free": "ฟรี",
    "flexible": "มีตัวเลือกปลดล็อกครั้งเดียว และแบบสมัครสมาชิกให้เลือก",
  },
  "vi": {
    "paid_upfront": "Trả một lần, không thuê bao.",
    "free_with_lifetime_unlock": "Tải miễn phí, mở khoá bằng một lần trả.",
    "free": "Miễn phí.",
    "flexible": "Có tuỳ chọn mở khoá một lần; gói thuê bao là tuỳ chọn.",
  },
  "pt-BR": {
    "paid_upfront": "Pagamento único, sem assinatura.",
    "free_with_lifetime_unlock": "Download grátis; desbloqueio em compra única com pagamento único.",
    "free": "Grátis.",
    "flexible": "Opção de desbloqueio único; assinaturas são opcionais.",
  },
  "de-DE": {
    "paid_upfront": "Einmalkauf, kein Abo.",
    "free_with_lifetime_unlock": "Kostenloser Download, einmalige Freischaltung.",
    "free": "Kostenlos.",
    "flexible": "Einmalige Freischaltung möglich; Abos sind optional.",
  },
  "ms": {
    "paid_upfront": "Bayar sekali, tiada langganan.",
    "free_with_lifetime_unlock": "Muat turun percuma; buka kunci dengan satu bayaran.",
    "free": "Percuma.",
    "flexible": "Ada pilihan buka kunci sekali; langganan adalah pilihan.",
  },
  "zh-Hant": {
    "paid_upfront": "一次買斷,沒有訂閱。",
    "free_with_lifetime_unlock": "免費下載,一次買斷解鎖完整功能。",
    "free": "免費。",
    "flexible": "有一次買斷解鎖選項,訂閱為選配。",
  },
  "es-ES": {
    "paid_upfront": "Pago único, sin suscripción.",
    "free_with_lifetime_unlock": "Descarga gratis; desbloqueo con un pago único.",
    "free": "Gratis.",
    "flexible": "Opción de desbloqueo único; las suscripciones son opcionales.",
  },
  "fr-FR": {
    "paid_upfront": "Achat unique, sans abonnement.",
    "free_with_lifetime_unlock": "Téléchargement gratuit ; déblocage en un seul achat.",
    "free": "Gratuit.",
    "flexible": "Déblocage unique possible ; les abonnements sont facultatifs.",
  },
}
