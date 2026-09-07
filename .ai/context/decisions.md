# Decision Log (Nhật Ký Quyết Định Kiến Trúc – ADR)

> 🎯 **Mục đích**: Ghi lại *vì sao* dự án chọn cách làm hiện tại, và **đã loại bỏ phương án nào**.
>
> ⚠️ **Vì sao file này quan trọng với AI Agent**: nếu không có, agent ở phiên sau sẽ "cải tiến" bằng cách
> đập đi làm lại đúng thứ mà bạn đã cân nhắc và cố ý chọn. Đây là lỗi kinh điển của quy trình đa-agent.
>
> 🔄 **Khi nào ghi**: mỗi khi có lựa chọn khó đảo ngược — chọn thư viện, chọn kiến trúc, chọn CSDL,
> chọn định dạng dữ liệu, cố ý không làm một việc gì đó.
>
> 📋 Dùng mẫu tại `.ai/templates/adr.md`. Quyết định mới nhất đặt trên cùng.

---

## ADR-013 — Tạm tắt provider fallback cho tới khi kiểm chứng lại

- **Ngày**: 2026-09-07
- **Trạng thái**: `Đang áp dụng`
- **Bối cảnh**: Các provider fallback đang cấu hình trả lỗi hoặc không ổn định. Nếu giữ cơ chế
  tự rơi sang chúng, lỗi của Gemini sẽ bị nối tiếp bằng một lỗi provider khác và làm khó chẩn đoán.
  Gemini `gemini-3.5-flash-lite` vẫn là provider chính; quota đã chốt ở 15 RPM / 250.000 TPM /
  500 RPD theo project Google.
- **Quyết định**: Đặt `FALLBACK_ENABLED=false` trên Render và trong mẫu môi trường. Giữ nguyên
  adapter OpenAI-compatible để bật lại bằng cấu hình sau khi có provider/model/key đã kiểm chứng.
- **Lý do**: Không gửi dữ liệu hội thoại sang provider chưa đạt kiểm tra; lỗi Gemini phải đi qua
  nhánh trả lời suy giảm an toàn thay vì gọi tiếp một endpoint đang lỗi.
- **Phương án đã loại**:
  - Tiếp tục giữ TokenRouter/OpenRouter làm đường lui mặc định — loại vì cả hai chưa có kết quả
    ổn định ở thời điểm deploy này.
  - Xóa hẳn mã fallback — loại vì sau này chỉ cần bật cờ và đổi biến môi trường là có thể dùng lại.
- **Hệ quả**: Khi Gemini hết quota hoặc lỗi, người dùng nhận thông báo suy giảm an toàn cho tới khi
  bật một provider fallback đã kiểm chứng. `GEMINI_RPM=15` được client tự giãn nhịp; TPM/RPD do
  Google áp dụng, không phải quota có thể chỉnh bằng Render env.

---

## ADR-012 — Tự giãn nhịp gọi Gemini phía client (15 lần/phút, theo từng model)

- **Ngày**: 2026-08-26
- **Trạng thái**: `Đang áp dụng`
- **Bối cảnh**: Bảng hạn mức của Google cho thấy `Gemini 3.5 Flash Lite` ở mức
  **RPM 18/15 (vượt)** trong khi **RPD chỉ 60/500** và **TPM 8,51K/250K**. Tức là dự án
  chưa hề cạn hạn mức ngày — nó chỉ **bắn quá nhanh trong một phút**.
  Bộ eval đang gọi khoảng **37 lần/phút** vào giới hạn 15, và chỉ "sống sót" nhờ cơ chế
  thử lại và rơi sang provider dự phòng.
- **Quyết định**: Thêm `_RateLimiter` (cửa sổ trượt 60 giây, dùng chung toàn tiến trình,
  **một rổ riêng cho mỗi model**) chặn trước mọi lời gọi Gemini, kể cả embedding.
  Ngưỡng đọc từ `GEMINI_RPM`, mặc định 15.
- **Lý do**:
  - Chờ chủ động rẻ hơn hẳn so với ăn 429 rồi thử lại: mỗi lần 429 tốn một vòng khứ hồi
    mạng, một khoảng backoff, rồi vẫn phải gọi lại.
  - **Lấy cơ chế chịu lỗi ra để che một lỗi nhịp độ là dùng sai công cụ.** Provider dự phòng
    phải để dành cho lúc Gemini thật sự hỏng, không phải để gánh việc mình tự bắn quá tay.
  - Chính đợt 429 dồn dập này đã khiến tôi chẩn đoán nhầm nguyên nhân của lỗi 400 ở D6.
- **Hệ quả cần biết**: hạn mức tính **theo từng model**. Từ ADR-010, router và bước trả lời
  **cùng dùng** `gemini-3.5-flash-lite`, nên chúng **chia chung một rổ 15 lần/phút**.
  Mỗi lượt hội thoại tiêu 2 lần gọi → trần khoảng **7 lượt/phút**.
  Đủ cho demo và cho eval, nhưng nếu cần thông lượng cao hơn thì tách bước trả lời sang
  `gemini-3.5-flash` để có rổ riêng — đổi lại TTFT tăng từ ~1,2s lên ~2,9s (ADR-010).
- **Phương án đã loại**:
  - Dùng nhiều API key để lách hạn mức — loại vì hạn mức tính theo project chứ không theo
    khoá, nên nhiều khoá cùng project không tăng thêm gì; và đây không phải cách xử lý
    đúng vấn đề.
  - Chỉ tăng `--delay` của eval — loại vì chỉ vá riêng bộ eval, còn máy chủ thật vẫn bắn tự do.

---

## ADR-011 — Provider dự phòng: TokenRouter (`qwen/qwen3.8-max-free`)

- **Ngày**: 2026-08-26
- **Trạng thái**: `Đang áp dụng` — thay phần chọn provider dự phòng của ADR-001.
- **Bối cảnh**: Đường lui của ADR-001 đã chết: OpenRouter trả `402 Payment Required`
  (hết credit), AgentRouter trả `401 unauthorized client detected` với cả 4 cách xác thực.
  Không có đường lui nghĩa là Gemini hết hạn mức lúc demo thì agent chỉ còn biết xin lỗi.
- **Quyết định**: Dùng TokenRouter (`https://api.tokenrouter.com/v1`, chuẩn OpenAI) với
  `qwen/qwen3.8-max-free` làm **provider dự phòng**. Gemini vẫn là chính.
- **Số đo thực tế** (mỗi cấu hình 2 lần):

  | Cấu hình | TTFT | Ghi chú |
  |---|---|---|
  | Mặc định (không chỉnh gì) | **21.097 ms** | 150/165 token đầu ra là `reasoning_tokens` |
  | `max_tokens=300` + structured output | không ra chữ nào | 301 reasoning token, **0 ký tự nội dung** |
  | `reasoning_effort=low`, trả lời tự do | 2.160 / 5.790 ms | dao động mạnh |
  | `reasoning_effort=low` + `json_schema`, `max_tokens≥600` | **1.464 / 1.397 ms** | ổn định |
  | Qua đường lui thật (ép Gemini hỏng) | **2.910 / 1.476 ms** | |

- **Lý do**:
  - **Miễn phí** — giải quyết đúng lỗ hổng mà không tiêu $5 nào.
  - Ổn định ở đường router (structured output ~1,4s), chấp nhận được ở đường trả lời.
  - Không bịa số liệu khi thiếu ngữ cảnh: hỏi phí huỷ mà không đưa tri thức thì nó trả
    "chưa có thông tin chính xác" thay vì đoán một con số.
- **Vì sao KHÔNG làm provider chính**: TTFT đường trả lời dao động 1,3–6,9 giây, tức có lúc
  vượt gấp đôi ngưỡng 3 giây. Gemini Flash-Lite đo được 1,2 giây và ổn định hơn hẳn.
- **Phương án đã loại**:
  - Mua $5 API OpenAI làm đường lui — loại vì TokenRouter miễn phí đã đủ. Tính ra $5 với
    `gpt-5.6-sol` chỉ đủ ~360 lượt, còn phần việc còn lại của dự án cần khoảng $19.
  - `enable_thinking=false` để tắt suy luận — **API từ chối**: *"Qwen3.8 open text checkpoints
    require thinking"*. Chỉ hạ được xuống `reasoning_effort=low`.
  - Bỏ hẳn provider dự phòng — loại vì đó chính là hạng mục "fallback khi lỗi" của đề bài.
- **Hệ quả — ba tham số bắt buộc, thiếu là hỏng**:
  1. `FALLBACK_EXTRA_BODY={"reasoning_effort":"low"}` — thiếu thì TTFT là 21 giây.
  2. `FALLBACK_MIN_MAX_TOKENS=800` — thiếu thì phần suy luận nuốt hết hạn mức và trả về **rỗng**.
  3. Phải truyền `response_format` kèm schema đã chuyển sang JSON Schema chuẩn
     (`_to_json_schema`). Thiếu thì model tự bịa tên trường (`trip_id` thay `ride_code`),
     slot rơi hết, và agent hỏi lại khách thông tin khách vừa mới nói.
- **Cảnh báo**: khoá đã bị dán vào khung chat — nên thu hồi và cấp lại sau khi xong dự án.

---

## ADR-010 — Dùng `gemini-3.5-flash-lite` cho CẢ bước trả lời (thay `gemini-3.5-flash`)

- **Ngày**: 2026-08-26
- **Trạng thái**: `Đang áp dụng` — thay phần chọn model trả lời của ADR-008, phần còn lại giữ nguyên.
- **Bối cảnh**: Kiểm chứng trên bản đã deploy (Render, vùng Singapore) cho TTFT **4.156 ms** và
  **3.609 ms** — vượt ngưỡng 3 giây của đề bài. Ở máy cục bộ cùng prompt đó cũng đã sát mép.
  Đo đối chứng trên đúng prompt trả lời thật (~2.950 ký tự, gồm 3 đoạn tri thức):

  | Model | TTFT 3 lần | Trung vị |
  |---|---|---|
  | `gemini-3.5-flash` | 3.017 / 2.791 / 2.951 ms | **2.951 ms** |
  | `gemini-3.5-flash-lite` | 1.243 / 1.203 / 1.467 ms | **1.243 ms** |

- **Quyết định**: `LLM_ANSWER_MODEL=gemini-3.5-flash-lite`. Router vẫn là `gemini-3.5-flash-lite`
  như ADR-008. Tức cả hai bước dùng chung một model.
- **Lý do**:
  - Nhanh hơn **2,4 lần**, đưa TTFT từ sát ngưỡng xuống còn khoảng một phần ba ngân sách.
    Biên an toàn này là thứ cần thiết vì Render free tier và đường mạng tới Gemini đều biến động.
  - **Chất lượng không tụt ở tác vụ này.** Bước trả lời đã được neo chặt vào RAG và kết quả tool
    trong prompt — đây đúng là loại việc mà model nhỏ làm tốt. Kiểm 3 câu có đáp án số cụ thể
    (phí huỷ taxi 20.000đ, phí huỷ Bike 10.000đ, hoàn tiền thẻ quốc tế 7–14 ngày): **đúng cả 3**.
  - Rẻ hơn, giúp ngân sách token của gói free đi xa hơn.
- **Phương án đã loại**:
  - Giữ `gemini-3.5-flash` và cắt ngắn prompt — loại vì cắt tri thức truy hồi sẽ làm hại độ chính
    xác, mà vẫn chưa chắc đủ để về dưới 3 giây.
  - Nâng gói Render để bớt nghẽn CPU — loại vì phần lớn độ trễ nằm ở phía model, không phải CPU.
- **Hệ quả**:
  - Phải đổi biến `LLM_ANSWER_MODEL` **trên dashboard Render**, không chỉ ở `.env` máy cá nhân.
  - Nếu sau này thêm tác vụ suy luận nhiều bước không có RAG neo lại, phải đo lại chất lượng
    trước khi vẫn dùng flash-lite cho tác vụ đó.

---

## ADR-009 — Số tiền hoàn do hệ thống suy ra từ bằng chứng, không lấy theo lời khai của khách

- **Ngày**: 2026-08-26
- **Trạng thái**: `Đang áp dụng`
- **Bối cảnh**: Bản đầu của graph bắt buộc router phải trích được slot `amount` rồi mới
  xử lý hoàn tiền; thiếu thì hỏi lại khách. Chạy thử thấy hai vấn đề: (1) LLM trích số
  tiền không ổn định — cùng một dạng câu, có lần ra `amount`, có lần không; (2) quan trọng
  hơn, **thiết kế đó sai về bản chất**: khách thường không biết mình được hoàn bao nhiêu,
  và để khách tự khai số tiền là mở đường cho gian lận.
- **Quyết định**: `derive_refund_evidence(ride_code)` đối soát dữ liệu chuyến và tự xác định
  khách có đủ điều kiện hay không, được hoàn bao nhiêu, theo thứ tự: thu tiền trùng → phí huỷ
  thu sai → đi vòng vượt ngưỡng → chênh lệch cước → gián đoạn dịch vụ. Trả `None` nghĩa là
  **không đủ điều kiện**, và đó là kết quả hợp lệ. Lời khai của khách chỉ dùng làm ngữ cảnh
  ghi vào `reason_detail`, không dùng làm số tiền.
- **Lý do**: Cùng một tinh thần với ADR-005 và ADR-006 — thứ gì mất tiền thật thì không để
  cho LLM hay cho lời khai quyết định. Ngoài ra nó biến các case âm trong seed
  (`XSM-DETOUR-02`, `XSM-CANCELFEE-02`) thành thứ kiểm chứng được: agent phải **từ chối đúng**,
  chứ không chỉ biết đồng ý đúng.
- **Phương án đã loại**:
  - Lấy `amount` từ slot của router — loại vì không ổn định và vì mời gọi gian lận.
  - Hỏi lại khách số tiền — loại vì khách không có cách nào biết, và làm hỏng trải nghiệm.
  - Cho LLM tự tính từ dữ liệu chuyến — loại vì số học trên tiền không nên nằm trong model.
- **Hệ quả**: Thêm một tool ảo `refund_eligibility` trong tool trace để CSKH thấy được căn cứ
  đối soát. Mỗi lý do hoàn tiền mới phải bổ sung một nhánh trong `derive_refund_evidence`.

---

## ADR-008 — Ghim `gemini-3.5-flash-lite` cho router và `gemini-3.5-flash` cho trả lời

- **Ngày**: 2026-08-26
- **Trạng thái**: `Đang áp dụng` — bổ sung chi tiết cho ADR-001, không thay thế nó.
- **Bối cảnh**: ADR-001 chốt "Gemini Flash" nhưng chưa chốt bản nào. Đã đo TTFT thật bằng
  streaming SSE với key của dự án, mỗi cấu hình 2 lần, prompt tiếng Việt ngắn:

  | Model | TTFT lần 1 | TTFT lần 2 | Kết luận |
  |---|---|---|---|
  | `gemini-3.5-flash-lite` | 0,96s | 0,86s | ✅ nhanh nhất |
  | `gemini-flash-lite-latest` | 1,05s | 0,90s | ✅ nhưng là alias, không ghim được |
  | `gemini-3.5-flash` | 2,07s | 2,04s | ✅ còn biên an toàn |
  | `gemini-3.1-flash-lite` | 3,78s | 3,60s | ❌ vượt ngưỡng |
  | `gemini-3.6-flash` | 5,10s | 5,94s | ❌ vượt ngưỡng xa |
  | `gemini-3.7-flash` | timeout > 30s | timeout > 30s | ❌ không dùng được |
  | `gemini-flash-latest` | timeout > 30s | timeout > 30s | ❌ alias trỏ vào bản chậm |
  | `gemini-2.5-flash`, `-lite` | HTTP 404 | — | ❌ không còn mở cho tài khoản mới |

- **Quyết định**:
  - Router (phân loại intent + trích slot): **`gemini-3.5-flash-lite`**
  - Sinh câu trả lời / gọi tool: **`gemini-3.5-flash`**
  - Embedding: **`gemini-embedding-001`** với `outputDimensionality=768`
  - **Cấm dùng alias `-latest`** ở mọi nơi.
- **Lý do**:
  - **Model mới hơn không hề nhanh hơn.** 3.6 và 3.7 chậm hơn 3.5 nhiều lần — nếu chọn theo
    số hiệu phiên bản thì đã phá ngưỡng 3 giây ngay từ ngày đầu mà không hiểu vì sao.
  - Alias `-latest` khiến kết quả eval không tái lập được, và có thể tự trỏ sang bản chậm
    bất cứ lúc nào — `gemini-flash-latest` timeout ngay trong phép đo này.
  - 768 chiều là bắt buộc: `gemini-embedding-001` mặc định trả 3072 chiều, còn index HNSW
    của pgvector chỉ hỗ trợ tối đa 2000 chiều.
- **Phương án đã loại**:
  - `gemini-2.5-flash` (bản mà tài liệu phổ biến hay nhắc) — loại vì trả **HTTP 404,
    không còn mở cho tài khoản mới**.
  - Dùng alias `-latest` cho tiện — loại vì phá tính tái lập của eval.
  - Dùng cùng một model cho cả router và trả lời — loại vì router chạy mọi lượt, tiết kiệm
    ~1,1s ở đó là khoản rẻ nhất trong toàn bộ ngân sách độ trễ.
- **Hệ quả**:
  - Tên model nằm trong `.env` (`LLM_ROUTER_MODEL`, `LLM_ANSWER_MODEL`), không hardcode.
  - **Đo lại bảng này trước khi đổi bất kỳ model nào.** Con số ở trên đo ngày 2026-08-26 từ
    Việt Nam; độ trễ phụ thuộc vùng và thời điểm.
  - Ngân sách 1,5s cho token đầu tiên trong `architecture.md` mục 5 vẫn đứng vững với 3.5-flash.

---

## ADR-007 — Python dùng `snake_case`, ghi đè quy ước `camelCase` trong coding-style

- **Ngày**: 2026-08-25
- **Trạng thái**: `Đang áp dụng`
- **Bối cảnh**: `.ai/rules/coding-style.md` quy định biến/hàm dùng `camelCase`. Quy ước này viết cho
  JavaScript/TypeScript, nhưng backend của dự án là Python (FastAPI, LangGraph, Pydantic).
  Viết `camelCase` trong Python sẽ xung đột với `ruff`/PEP 8 và với chính API của các thư viện đó.
- **Quyết định**: Backend Python theo PEP 8 (`snake_case` cho biến/hàm, `PascalCase` cho class,
  `UPPER_SNAKE_CASE` cho hằng). Frontend TypeScript giữ nguyên `camelCase` như coding-style.
  Tên **cột DB và trường JSON của API** dùng `snake_case` ở cả hai phía để không phải map qua lại.
- **Phương án đã loại**:
  - Ép `camelCase` cho Python — loại vì chống lại linter và toàn bộ hệ sinh thái thư viện.
  - `camelCase` cho JSON API, `snake_case` cho DB — loại vì phát sinh một tầng chuyển đổi vô ích.
- **Hệ quả**: `.ai/rules/coding-style.md` được bổ sung mục phân tách theo ngôn ngữ, trỏ về ADR này.

---

## ADR-006 — Chính sách nghiệp vụ là **dữ liệu**, không nằm trong prompt

- **Ngày**: 2026-08-25
- **Trạng thái**: `Đang áp dụng`
- **Bối cảnh**: Các con số nghiệp vụ (ngưỡng hoàn tiền tự động 50.000đ, phí chờ 60.000đ/giờ, cửa sổ
  huỷ miễn phí 2 phút…) được dùng ở nhiều nơi: router, tool, guardrail, dashboard.
- **Quyết định**: Toàn bộ ngưỡng và tham số nghiệp vụ nằm trong bảng `business_config` (key–value có
  version), đọc ra lúc chạy. Prompt và mã nguồn **không được hardcode** bất kỳ con số nghiệp vụ nào.
- **Lý do**: (1) Lúc demo có thể hạ ngưỡng ngay trên dashboard để kích hoạt luồng HITL trực tiếp trước
  người xem. (2) Đổi chính sách không phải sửa prompt rồi chạy lại toàn bộ eval.
  (3) Con số nằm trong prompt là thứ LLM hay diễn giải sai.
- **Phương án đã loại**:
  - Nhúng ngưỡng vào system prompt — loại vì LLM có thể hiểu sai và không kiểm toán được.
  - Để trong file `.env` — loại vì không đổi được lúc chạy, không có lịch sử thay đổi.
- **Hệ quả**: Cần một màn hình config nhỏ trên dashboard CSKH; mỗi lần đổi ngưỡng ghi vào `audit_log`.

---

## ADR-005 — Mọi tool ghi dữ liệu phải có `idempotency_key`

- **Ngày**: 2026-08-25
- **Trạng thái**: `Đang áp dụng`
- **Bối cảnh**: LLM có thể gọi lại cùng một tool khi timeout, khi người dùng nhắn lại, hoặc khi graph
  được resume sau HITL. Với `request_refund` và `book_ride`, gọi lặp nghĩa là hoàn tiền hai lần.
- **Quyết định**: `book_ride`, `cancel_ride`, `modify_ride`, `request_refund`, `create_ticket` đều nhận
  `idempotency_key` (hash của `conversation_id` + intent + tham số nghiệp vụ chính). Có ràng buộc
  `UNIQUE` ở tầng DB; gọi trùng thì trả lại kết quả cũ chứ không thực thi lần hai.
- **Lý do**: Đây là tầng bảo vệ duy nhất **không phụ thuộc vào việc LLM cư xử đúng**. Không vá được về
  sau vì nó là ràng buộc schema.
- **Phương án đã loại**:
  - Dặn LLM trong prompt là "đừng gọi lại" — loại vì lời dặn không phải là bảo đảm.
  - Khoá theo phiên ở tầng ứng dụng — loại vì không sống sót qua restart tiến trình.
- **Hệ quả**: Bảng `tool_calls` cần cột `idempotency_key UNIQUE`; tool phải trả lại được kết quả đã lưu.

---

## ADR-004 — PII được token hoá **trước khi** vào context của LLM

- **Ngày**: 2026-08-25
- **Trạng thái**: `Đang áp dụng`
- **Bối cảnh**: Đề bài bắt buộc che số điện thoại và điểm đón/đến. Cách phổ biến là lọc chuỗi đầu ra
  bằng regex, nhưng cách đó chỉ chặn được đúng định dạng đã lường trước — LLM vẫn có thể diễn giải lại
  ("số bắt đầu bằng không chín một…") và vẫn lộ.
- **Quyết định**: Token hoá ở **tầng truy cập dữ liệu**. Bản ghi lấy từ DB được thay PII bằng placeholder
  ổn định (`0912345678` → `<PHONE_C7>`, `12 Nguyễn Trãi` → `<ADDR_A3>`) trước khi đưa vào prompt.
  LLM làm việc trên placeholder; ánh xạ ngược chỉ diễn ra ở tầng render giao diện và chỉ cho vai trò
  được phép. Regex lọc đầu ra vẫn giữ, nhưng chỉ là lưới an toàn lớp hai.
- **Lý do**: LLM không thể làm lộ thứ nó chưa từng nhìn thấy. Đây là bảo đảm kiến trúc, không phải bộ
  lọc may rủi.
- **Phương án đã loại**:
  - Chỉ lọc regex ở đầu ra — loại vì thua trước prompt injection và trước cách diễn đạt vòng vo.
  - Che ngay trong DB — loại vì CSKH cần thấy dữ liệu thật để xử lý ca.
- **Hệ quả**: Cần module `pii/tokenizer.py` giữ bảng ánh xạ theo phiên; mọi tool đọc dữ liệu phải đi qua
  nó. Bộ red-team 20 prompt trong eval là thước đo bắt buộc của quyết định này.
- **Kết quả đã kiểm chứng (T-010, 2026-08-26)** — quyết định này đúng, và số đo chứng minh:

  | Tầng bảo vệ | Số ca lộ / 20 |
  |---|---|
  | Chỉ dặn trong system prompt | **5** |
  | Thêm lưới regex ở đầu ra | **2** |
  | Token hoá trước khi vào context | **0** ✅ |

  Hai điều học được khi hiện thực hoá:
  1. Che ở **cuối** luồng là không đủ. Bản đầu chỉ che biến `answer` sau vòng lặp stream,
     nên DB thì sạch mà **màn hình khách vẫn hiện `<ADDR_48>`**. Phải che ngay trên từng
     mảnh, và chịu được placeholder bị cắt đôi giữa hai mảnh (`StreamMasker`).
  2. `tool_calls` vẫn lưu **giá trị thật**: CSKH có quyền xem, và tool trace mất PII thì
     không xử lý được ca. Chỉ nhánh đi vào context của LLM mới bị token hoá.

---

## ADR-003 — HITL bằng `interrupt()` + checkpointer Postgres của LangGraph

- **Ngày**: 2026-08-25
- **Trạng thái**: `Đang áp dụng`
- **Bối cảnh**: Cần dừng agent giữa chừng khi khoản hoàn tiền vượt ngưỡng, chờ CSKH duyệt, rồi **đi tiếp**.
- **Quyết định**: Dùng cơ chế `interrupt()` của LangGraph với checkpointer lưu trên Postgres.
  Trạng thái graph được ghi tại điểm dừng; khi CSKH duyệt hoặc từ chối, graph resume từ đúng chỗ đó và
  trả kết quả về hội thoại của khách qua WebSocket.
- **Lý do**: Đây là khác biệt lớn nhất so với cách làm phổ thông ("tạo ticket rồi kết thúc hội thoại").
  Checkpointer trên Postgres còn cho phép resume sau khi server restart — chuyện thường xảy ra trên gói
  free của Render.
- **Phương án đã loại**:
  - Tạo ticket rồi đóng hội thoại, khách quay lại hỏi sau — loại vì mất hoàn toàn ngữ cảnh nhiều bước.
  - Checkpointer trong bộ nhớ — loại vì Render free tier ngủ rồi khởi động lại, mất hết ca đang chờ duyệt.
  - Tự viết hàng đợi phê duyệt riêng — loại vì tốn 2 ngày làm lại thứ framework đã có sẵn.
- **Hệ quả**: Cần bảng checkpoint của LangGraph trên Postgres, và một kênh đẩy (WebSocket) từ hành động
  của CSKH về đúng phiên của khách.
- **Kết quả đã kiểm chứng (T-011, 2026-08-26)** — `tests.test_hitl_flow` đạt **26/26**:
  graph dừng thật, state nằm trong bảng `checkpoints` của Postgres, CSKH duyệt xong thì graph
  chạy tiếp và khách nhận thông báo **ngay trên phiên đang mở** (server xác nhận đã đẩy).

  Ba điều học được khi hiện thực hoá:
  1. **`interrupt()` chạy LẠI cả node từ đầu khi resume**, chứ không tiếp tục từ giữa hàm.
     Nghĩa là mọi lời gọi tool phía trên chạy lại. Đây đúng là chỗ ADR-005 trả công:
     `request_refund` trùng `idempotency_key` nên trả kết quả cũ với `replayed=True` — kiểm
     chứng bằng truy vấn `count(*) = 1`. Không có idempotency thì mỗi lần duyệt là một
     yêu cầu hoàn tiền mới.
  2. **Thứ tự ghi–rồi–đánh thức là bắt buộc.** Ghi quyết định xuống DB trước, resume graph sau.
     Đảo lại mà bước ghi hỏng thì khách đã nhận thông báo "được duyệt" trong khi hệ thống
     không có bản ghi nào.
  3. Trên Windows, `psycopg` bản async **không chạy được** trên `ProactorEventLoop` mà uvicorn
     chọn mặc định. Phải dùng `run_dev.py` (đặt `WindowsSelectorEventLoopPolicy` + `loop="none"`).
     Linux không dính, nên production không phải đổi gì.

---

## ADR-002 — Dùng `pgvector` trên Postgres, không dùng Qdrant

- **Ngày**: 2026-08-25
- **Trạng thái**: `Đang áp dụng`
- **Bối cảnh**: Đề bài cho phép chọn Qdrant hoặc pgvector. Kho tri thức hiện chỉ có 7 file / 416 dòng.
- **Quyết định**: Một Postgres duy nhất (Neon hoặc Supabase gói free) chứa cả dữ liệu nghiệp vụ,
  checkpoint của LangGraph, và vector embedding qua `pgvector`.
- **Lý do**: Tiết kiệm trọn một ngày dựng, deploy và đồng bộ hạ tầng thứ hai. Kho tri thức chưa tới
  ngưỡng cần vector DB chuyên dụng. Truy hồi và truy vấn nghiệp vụ nằm chung một transaction.
- **Phương án đã loại**:
  - Qdrant Cloud — loại vì thêm một hạ tầng, một bộ credential, một điểm hỏng, đổi lại lợi ích gần bằng
    không ở quy mô này.
  - FAISS trong bộ nhớ — loại vì mất index mỗi lần Render khởi động lại.
- **Hệ quả**: Nếu kho tri thức vượt khoảng 50k chunk thì phải xem xét lại — ghi ADR mới, đừng sửa ADR này.

---

## ADR-001 — LLM: Gemini Flash làm chính, OpenRouter làm đường lui

- **Ngày**: 2026-08-25
- **Trạng thái**: `Đang áp dụng`
- **Bối cảnh**: Người dùng có sẵn API key của Gemini và OpenRouter. Đề bài gợi ý GPT-4o-mini hoặc
  Gemini Flash. Ràng buộc phản hồi < 3s và kiểm soát chi phí token đều nghiêng về model nhỏ, nhanh.
- **Quyết định**: **Gemini Flash cho mọi node** (router, trả lời RAG, gọi tool). **OpenRouter là provider
  dự phòng**, tự động chuyển sang khi Gemini trả 429 hoặc 5xx. Bọc trong một lớp `LLMClient` mỏng
  (~80 dòng) theo mô hình `primary → fallback`. ID model cụ thể phải lấy từ API list-models bằng key
  thật, **không hardcode theo trí nhớ**.
- **Lý do**: Gemini Flash có độ trễ thấp nhất trong tầm giá và gói free đủ cho demo. Cơ chế chuyển
  provider đồng thời chính là hạng mục "fallback khi lỗi" mà đề bài yêu cầu ở phần nâng cao — làm một
  lần, tính điểm hai chỗ.
- **Phương án đã loại**:
  - LiteLLM để trừu tượng hoá đa provider — loại vì tốn nửa ngày cấu hình cho nhu cầu chỉ có hai provider.
  - GPT-4o-mini làm chính — loại vì không có sẵn key, và không nhanh hơn Flash đủ để bù chi phí.
  - Model lớn cho node reasoning — loại vì phá ngưỡng 3 giây.
- **Hệ quả**: Gói free của Gemini giới hạn theo phút → **bắt buộc** cache embedding của kho tri thức
  (index một lần, lưu DB) và cache câu trả lời FAQ, nếu không sẽ dính 429 ngay giữa buổi demo.

---

> *Thêm ADR mới phía trên dòng này.*
