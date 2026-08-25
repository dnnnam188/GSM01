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
