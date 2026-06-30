const API_BASE = "http://127.0.0.1:8000";

let selectedRecordId = null;
let currentRawStatus = "pending";
let cachedSources = [];
let candidateIncludeAll = false;

const CHINESE_FIELD_MAPPING = {
  "院校名称": "school_name",
  "院校代码": "school_code",
  "所在省份": "school_province",
  "城市": "city",
  "院校层次": "school_level",
  "专业名称": "major_name",
  "专业代码": "major_code",
  "专业类别": "major_category",
  "方向标签": "direction_tags",
  "年份": "admission_year",
  "招生省份": "admission_province",
  "科类": "subject_type",
  "批次": "batch",
  "专业组": "major_group_code",
  "院校专业组": "major_group_code",
  "选科": "elective_requirement",
  "选科要求": "elective_requirement",
  "最低分": "min_score",
  "最低位次": "min_rank",
  "招生人数": "plan_count",
  "学费": "tuition",
  "校区": "campus",
  "数据来源": "source_name",
  "来源链接": "source_url",
  "原始文本": "raw_text"
};

const HTML_PARSER_CONFIG = {
  table_index: 0,
  header_row_index: 0,
  auto_detect_header: true,
  header_keywords: ["科类", "院校专业组", "选科", "专业名称", "最低分", "最低位次"],
  header_min_match_count: 4,
  skip_rows: 0,
  fill_down_fields: ["subject_type", "major_group_code", "elective_requirement"],
  auto_direction_tags: true,
  major_filter_keywords: [
    "人工智能",
    "计算机",
    "软件工程",
    "软件",
    "数据科学",
    "大数据",
    "智能科学",
    "网络工程",
    "信息安全",
    "网络空间安全",
    "电子信息",
    "自动化",
    "机器人工程",
    "机械电子",
    "测控",
    "通信工程",
    "通信",
    "微电子",
    "集成电路",
    "物联网"
  ],
  default_values: {
    admission_province: "四川",
    subject_type: "物理类"
  }
};

const $ = (id) => document.getElementById(id);

function escapeHtml(value) {
  if (value === null || value === undefined || value === "") return "-";
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function setHtml(id, html) {
  const el = $(id);
  if (el) el.innerHTML = html;
}

function showMessage(text, type = "error") {
  const box = $("messageBox");
  if (!box) return;
  if (!text) {
    box.className = "message hidden";
    box.textContent = "";
    return;
  }
  box.className = `message ${type}`;
  box.textContent = text;
}

function showSuccess(text) {
  showMessage(text, "success");
}

function jsonBlock(value) {
  return `<pre class="json-block">${escapeHtml(JSON.stringify(value, null, 2))}</pre>`;
}

function badge(value, fallback = "-") {
  const text = value === null || value === undefined || value === "" ? fallback : String(value);
  const cls = text.toLowerCase().replaceAll("_", "-");
  return `<span class="tag ${escapeHtml(cls)}">${escapeHtml(text)}</span>`;
}

function compactText(value, length = 80) {
  if (!value) return "-";
  const text = String(value);
  return text.length > length ? `${text.slice(0, length)}...` : text;
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail = data && data.detail ? data.detail : data;
    throw new Error(detail || `请求失败：${response.status}`);
  }
  return data;
}

async function safeRun(fn, label) {
  try {
    await fn();
  } catch (error) {
    console.error(label, error);
    showMessage(`${label}失败：${error.message || error}`);
  }
}

function parseJsonTextarea(id) {
  const value = $(id)?.value.trim();
  if (!value) return null;
  JSON.parse(value);
  return value;
}

function renderSourceCard(item) {
  const detected = item.last_detected_type || "-";
  const official = item.official_check_status || "-";
  return `
    <article class="source-card">
      <div class="source-title">
        <strong>${escapeHtml(item.name)}</strong>
        <div class="tag-row">
          ${badge(item.enabled ? "enabled" : "disabled")}
          ${badge(item.parser_type)}
          ${badge(detected)}
          ${badge(official)}
        </div>
      </div>
      <div class="muted">ID: ${escapeHtml(item.id)} ｜ 学校：${escapeHtml(item.school_name)} ｜ 表格数：${escapeHtml(item.last_table_count)}</div>
      <div class="muted">官方分：${escapeHtml(item.official_score)} ｜ 候选状态：${escapeHtml(item.candidate_status)} ｜ reference_only：${escapeHtml(item.reference_only)}</div>
      <a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(compactText(item.url, 120))}</a>
      <p>${escapeHtml(item.description)}</p>
      <div class="button-row compact">
        <button class="btn btn-secondary" data-action="check-source" data-id="${escapeHtml(item.id)}">检测</button>
        <button class="btn btn-secondary" data-action="preview-source" data-id="${escapeHtml(item.id)}">预览解析</button>
        <button class="btn btn-success" data-action="run-source" data-id="${escapeHtml(item.id)}">单源采集</button>
        <button class="btn btn-secondary" data-action="extract-file-links" data-id="${escapeHtml(item.id)}">提取附件</button>
        <button class="btn btn-light" data-action="edit-source" data-id="${escapeHtml(item.id)}">编辑填入表单</button>
      </div>
    </article>
  `;
}

async function loadSources() {
  try {
    const sources = await request("/raw-data-sources");
    cachedSources = sources || [];
    if (!cachedSources.length) {
      setHtml("sourceList", '<div class="empty">暂无数据源。</div>');
      return;
    }
    setHtml("sourceList", cachedSources.map(renderSourceCard).join(""));
  } catch (error) {
    setHtml("sourceList", '<div class="empty">数据源加载失败。</div>');
    showMessage(error.message || "数据源加载失败");
  }
}

function resetSourceForm() {
  $("sourceForm")?.reset();
  if ($("sourceId")) $("sourceId").value = "";
  if ($("sourceEnabled")) $("sourceEnabled").checked = true;
  if ($("saveSourceBtn")) $("saveSourceBtn").textContent = "新增数据源";
}

function fillSourceForm(source) {
  if (!source) return;
  if ($("sourceId")) $("sourceId").value = source.id || "";
  if ($("sourceName")) $("sourceName").value = source.name || "";
  if ($("sourceSchoolName")) $("sourceSchoolName").value = source.school_name || "";
  if ($("sourceType")) $("sourceType").value = source.source_type || "";
  if ($("parserType")) $("parserType").value = source.parser_type || "";
  if ($("sourceEnabled")) $("sourceEnabled").checked = Boolean(source.enabled);
  if ($("sourceUrl")) $("sourceUrl").value = source.url || "";
  if ($("sourceDescription")) $("sourceDescription").value = source.description || "";
  if ($("fieldMappingJson")) $("fieldMappingJson").value = source.field_mapping_json || "";
  if ($("parserConfigJson")) $("parserConfigJson").value = source.parser_config_json || "";
  if ($("saveSourceBtn")) $("saveSourceBtn").textContent = "更新数据源";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function saveSource(event) {
  event.preventDefault();
  try {
    parseJsonTextarea("fieldMappingJson");
    parseJsonTextarea("parserConfigJson");
    const sourceId = $("sourceId")?.value;
    const payload = {
      name: $("sourceName")?.value.trim(),
      school_name: $("sourceSchoolName")?.value.trim() || null,
      source_type: $("sourceType")?.value.trim() || null,
      url: $("sourceUrl")?.value.trim() || null,
      parser_type: $("parserType")?.value || null,
      enabled: Boolean($("sourceEnabled")?.checked),
      description: $("sourceDescription")?.value.trim() || null,
      field_mapping_json: $("fieldMappingJson")?.value.trim() || null,
      parser_config_json: $("parserConfigJson")?.value.trim() || null
    };
    const method = sourceId ? "PATCH" : "POST";
    const path = sourceId ? `/raw-data-sources/${sourceId}` : "/raw-data-sources";
    await request(path, { method, body: JSON.stringify(payload) });
    showSuccess(sourceId ? "数据源已更新" : "数据源已新增");
    resetSourceForm();
    await loadSources();
  } catch (error) {
    showMessage(error.message || "保存数据源失败，请检查 JSON 格式");
  }
}

async function sourceAction(action, id) {
  try {
    if (action === "edit-source") {
      const source = cachedSources.find((item) => String(item.id) === String(id))
        || await request(`/raw-data-sources/${id}`);
      fillSourceForm(source);
      return;
    }

    const endpoints = {
      "check-source": { path: `/raw-data-sources/${id}/check`, method: "POST", target: "sourceDiagnosticsReport" },
      "preview-source": { path: `/collectors/preview-source/${id}`, method: "POST", target: "sourceDiagnosticsReport" },
      "run-source": { path: `/collectors/run-source/${id}`, method: "POST", target: "latestRunResult" },
      "extract-file-links": { path: `/raw-data-sources/${id}/extract-file-links`, method: "POST", target: "sourceDiagnosticsReport" }
    };
    const cfg = endpoints[action];
    if (!cfg) return;
    const result = await request(cfg.path, { method: cfg.method });
    setHtml(cfg.target, jsonBlock(result));
    showSuccess("操作完成");
    await Promise.allSettled([loadSources(), loadCollectorRuns(), loadRawRecords(currentRawStatus), loadSourceCandidates()]);
  } catch (error) {
    showMessage(error.message || "数据源操作失败");
  }
}

function renderCollectorResult(results) {
  const list = Array.isArray(results) ? results : [results];
  if (!list.length) return '<div class="empty">暂无运行结果。</div>';
  return `
    <table class="table">
      <thead><tr><th>source</th><th>parser</th><th>status</th><th>inserted</th><th>skipped</th><th>errors</th><th>run_id</th><th>message</th></tr></thead>
      <tbody>
        ${list.map((item) => `
          <tr>
            <td>${escapeHtml(item.source_name || item.name)}</td>
            <td>${escapeHtml(item.parser_type)}</td>
            <td>${badge(item.status)}</td>
            <td>${escapeHtml(item.inserted_count)}</td>
            <td>${escapeHtml(item.skipped_count)}</td>
            <td>${escapeHtml(item.error_count)}</td>
            <td>${escapeHtml(item.collector_run_id)}</td>
            <td class="message-cell">${escapeHtml(item.message)}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

async function runCollectors() {
  const button = $("runCollectorsBtn");
  try {
    if (button) button.disabled = true;
    setHtml("latestRunResult", '<div class="empty">采集器运行中，请稍候...</div>');
    const result = await request("/collectors/run", { method: "POST" });
    setHtml("latestRunResult", renderCollectorResult(result));
    showSuccess("采集器运行完成");
    await Promise.allSettled([loadCollectorRuns(), loadRawRecords(currentRawStatus), loadSources()]);
  } catch (error) {
    showMessage(error.message || "运行采集器失败");
  } finally {
    if (button) button.disabled = false;
  }
}

async function loadCollectorRuns() {
  try {
    const runs = await request("/collector-runs?limit=50");
    if (!runs || !runs.length) {
      setHtml("collectorRuns", '<div class="empty">暂无采集记录。</div>');
      return;
    }
    setHtml("collectorRuns", `
      <table class="table">
        <thead><tr><th>ID</th><th>source</th><th>parser</th><th>status</th><th>inserted</th><th>skipped</th><th>errors</th><th>started</th><th>finished</th><th>message</th></tr></thead>
        <tbody>
          ${runs.map((item) => `
            <tr>
              <td>${escapeHtml(item.id)}</td>
              <td>${escapeHtml(item.source_name)}</td>
              <td>${escapeHtml(item.parser_type)}</td>
              <td>${badge(item.status)}</td>
              <td>${escapeHtml(item.inserted_count)}</td>
              <td>${escapeHtml(item.skipped_count)}</td>
              <td>${escapeHtml(item.error_count)}</td>
              <td>${escapeHtml(item.started_at)}</td>
              <td>${escapeHtml(item.finished_at)}</td>
              <td class="message-cell">${escapeHtml(item.message)}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `);
  } catch (error) {
    setHtml("collectorRuns", '<div class="empty">采集记录加载失败。</div>');
    showMessage(error.message || "采集记录加载失败");
  }
}

async function bulkExtractFileLinks() {
  try {
    const result = await request("/bulk/extract-file-links?limit=20", { method: "POST" });
    setHtml("sourceDiagnosticsReport", jsonBlock(result));
    showSuccess("批量提取附件完成");
    await loadSources();
  } catch (error) {
    showMessage(error.message || "批量提取附件失败");
  }
}

function renderRawRecordCard(item) {
  return `
    <article class="record-card card-lite ${String(item.id) === String(selectedRecordId) ? "active" : ""}" data-id="${escapeHtml(item.id)}">
      <div class="record-title">
        <strong>${escapeHtml(item.school_name)} - ${escapeHtml(item.major_name)}</strong>
        ${badge(item.status)}
        ${item.is_duplicate ? badge("疑似重复") : ""}
      </div>
      <div class="muted">
        ${escapeHtml(item.admission_year)} ｜ ${escapeHtml(item.admission_province)} ｜ ${escapeHtml(item.subject_type)}
        ｜ 最低分 ${escapeHtml(item.min_score)} ｜ 位次 ${escapeHtml(item.min_rank)}
      </div>
      <div class="muted">${escapeHtml(compactText(item.source_name || item.source_url, 100))}</div>
    </article>
  `;
}

async function loadRawRecords(status = currentRawStatus) {
  currentRawStatus = status;
  try {
    const path = status ? `/raw-admission-records?status=${encodeURIComponent(status)}` : "/raw-admission-records";
    const records = await request(path);
    if (!records || !records.length) {
      setHtml("rawRecordList", '<div class="empty">暂无 raw 记录。</div>');
      return;
    }
    setHtml("rawRecordList", records.map(renderRawRecordCard).join(""));
  } catch (error) {
    setHtml("rawRecordList", '<div class="empty">raw 记录加载失败。</div>');
    showMessage(error.message || "raw 记录加载失败");
  }
}

function renderDetail(record) {
  const fields = [
    "id", "raw_source_id", "school_name", "school_code", "school_province", "city", "school_level", "school_tags",
    "major_name", "major_code", "major_category", "direction_tags", "major_description", "career_paths",
    "admission_year", "admission_province", "subject_type", "batch", "major_group_code", "elective_requirement",
    "min_score", "min_rank", "plan_count", "tuition", "campus", "source_name", "source_url", "raw_text",
    "status", "error_message", "is_duplicate", "created_at", "updated_at"
  ];
  return `
    <dl class="detail-grid">
      ${fields.map((field) => `
        <dt>${escapeHtml(field)}</dt>
        <dd>${field === "source_url" && record[field]
          ? `<a href="${escapeHtml(record[field])}" target="_blank" rel="noopener noreferrer">${escapeHtml(record[field])}</a>`
          : escapeHtml(record[field])}
        </dd>
      `).join("")}
    </dl>
  `;
}

function setRecordButtons(enabled) {
  if ($("verifyRecordBtn")) $("verifyRecordBtn").disabled = !enabled;
  if ($("rejectRecordBtn")) $("rejectRecordBtn").disabled = !enabled;
}

async function loadRawRecordDetail(id) {
  try {
    selectedRecordId = id;
    const record = await request(`/raw-admission-records/${id}`);
    setHtml("rawRecordDetail", renderDetail(record));
    setRecordButtons(record.status === "pending");
    await loadRawRecords(currentRawStatus);
  } catch (error) {
    showMessage(error.message || "记录详情加载失败");
  }
}

async function verifySelectedRecord() {
  if (!selectedRecordId) return;
  try {
    const result = await request(`/raw-admission-records/${selectedRecordId}/verify`, { method: "POST" });
    showSuccess(result.message || "核验成功，已写入正式推荐库");
    selectedRecordId = null;
    setRecordButtons(false);
    setHtml("rawRecordDetail", '<div class="empty">请选择左侧记录。</div>');
    await loadRawRecords(currentRawStatus);
  } catch (error) {
    showMessage(error.message || "核验失败");
  }
}

async function rejectSelectedRecord() {
  if (!selectedRecordId) return;
  try {
    await request(`/raw-admission-records/${selectedRecordId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status: "rejected", error_message: "管理员核验驳回" })
    });
    showSuccess("已驳回");
    selectedRecordId = null;
    setRecordButtons(false);
    setHtml("rawRecordDetail", '<div class="empty">请选择左侧记录。</div>');
    await loadRawRecords(currentRawStatus);
  } catch (error) {
    showMessage(error.message || "驳回失败");
  }
}

async function generateCoverageReport() {
  try {
    const result = await request("/bulk/generate-coverage-report?province=四川&year=2025", { method: "POST" });
    setHtml("coverageReport", jsonBlock(result));
    showSuccess("覆盖率报告已生成");
  } catch (error) {
    showMessage(error.message || "生成覆盖率报告失败");
  }
}

async function generateGapDiagnosisReport() {
  try {
    const result = await request("/gap-diagnosis/generate?province=四川&year=2025", { method: "POST" });
    setHtml("gapDiagnosisReport", jsonBlock(result));
    showSuccess("缺口诊断报告已生成");
  } catch (error) {
    showMessage(error.message || "生成缺口诊断报告失败");
  }
}

async function loadLatestReports() {
  try {
    const coverage = await request("/bulk/coverage-reports?limit=1");
    if (coverage && coverage.length) setHtml("coverageReport", jsonBlock(coverage[0]));
  } catch {
    setHtml("coverageReport", '<div class="empty">覆盖率报告加载失败或暂无报告。</div>');
  }

  try {
    const gap = await request("/gap-diagnosis/latest");
    if (gap) setHtml("gapDiagnosisReport", jsonBlock(gap));
  } catch {
    setHtml("gapDiagnosisReport", '<div class="empty">缺口诊断报告加载失败或暂无报告。</div>');
  }
}

async function backfillSourceSchoolNames() {
  try {
    const result = await request("/source-diagnostics/backfill-school-names", { method: "POST" });
    setHtml("sourceDiagnosticsReport", jsonBlock(result));
    showSuccess("数据源学校归属回填完成");
    await loadSources();
  } catch (error) {
    showMessage(error.message || "回填失败");
  }
}

async function diagnoseSourcesWithoutRecords() {
  try {
    const result = await request("/source-diagnostics/diagnose-without-records?limit=50", { method: "POST" });
    setHtml("sourceDiagnosticsReport", jsonBlock(result));
    showSuccess("诊断完成");
  } catch (error) {
    showMessage(error.message || "诊断失败");
  }
}

async function generateSourceActionQueue() {
  try {
    const result = await request("/source-diagnostics/action-queue", { method: "POST" });
    setHtml("sourceDiagnosticsReport", jsonBlock(result));
    showSuccess("处理队列已生成");
  } catch (error) {
    showMessage(error.message || "生成处理队列失败");
  }
}

function renderCandidates(candidates) {
  if (!candidates || !candidates.length) {
    return '<div class="empty">暂无候选数据源。</div>';
  }
  return `
    <table class="table">
      <thead>
        <tr>
          <th>ID</th>
          <th>学校</th>
          <th>官方状态</th>
          <th>官方分</th>
          <th>候选状态</th>
          <th>解析器</th>
          <th>URL</th>
          <th>说明</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        ${candidates.map((item) => {
          const canApprove = (item.candidate_status || "pending") === "pending"
            && ["official", "likely_official"].includes(item.official_check_status)
            && !item.reference_only;
          return `
            <tr>
              <td>${escapeHtml(item.id)}</td>
              <td>${escapeHtml(item.school_name)}</td>
              <td>${badge(item.official_check_status || "unchecked")}</td>
              <td>${escapeHtml(item.official_score)}</td>
              <td>${badge(item.candidate_status || "pending")}${item.reference_only ? badge("reference_only") : ""}</td>
              <td>${escapeHtml(item.parser_type)}</td>
              <td><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">打开链接</a></td>
              <td class="message-cell">
                <div>${escapeHtml(item.official_check_message || item.description)}</div>
                ${item.candidate_reject_reason ? `<div class="danger-text">拒绝原因：${escapeHtml(item.candidate_reject_reason)}</div>` : ""}
              </td>
              <td>
                <div class="button-row compact">
                  ${canApprove ? `<button class="btn btn-success" data-candidate-action="approve" data-id="${escapeHtml(item.id)}">确认启用</button>` : ""}
                  ${(item.candidate_status || "pending") === "pending" ? `<button class="btn btn-danger" data-candidate-action="reject" data-id="${escapeHtml(item.id)}">驳回</button>` : ""}
                  <button class="btn btn-secondary" data-candidate-action="check" data-id="${escapeHtml(item.id)}">检测</button>
                  <button class="btn btn-secondary" data-candidate-action="preview" data-id="${escapeHtml(item.id)}">预览解析</button>
                </div>
              </td>
            </tr>
          `;
        }).join("")}
      </tbody>
    </table>
  `;
}

async function loadSourceCandidates(includeAll = candidateIncludeAll) {
  candidateIncludeAll = includeAll;
  try {
    const candidates = await request(`/source-candidates?limit=100&include_all=${includeAll ? "true" : "false"}`);
    setHtml("sourceCandidatesList", renderCandidates(candidates));
  } catch (error) {
    setHtml("sourceCandidatesList", '<div class="empty">候选源加载失败。</div>');
    showMessage(error.message || "候选源加载失败");
  }
}

async function deepSearchMissingSources() {
  try {
    setHtml("sourceCandidatesList", '<div class="empty">深度搜索中，可能消耗搜索 API 额度，请稍候...</div>');
    const result = await request("/source-candidates/deep-search-missing?limit=20", { method: "POST" });
    setHtml("sourceDiagnosticsReport", jsonBlock(result));
    showSuccess("深度搜索完成，候选源已保存。");
    await loadSourceCandidates();
  } catch (error) {
    showMessage(error.message || "深度搜索缺失学校失败");
  }
}

async function filterOfficialCandidates() {
  try {
    const result = await request("/source-candidates/filter-official?limit=500", { method: "POST" });
    setHtml("sourceDiagnosticsReport", jsonBlock(result));
    showSuccess("官方候选过滤完成");
    await Promise.allSettled([loadSourceCandidates(), loadSources()]);
  } catch (error) {
    showMessage(error.message || "官方候选过滤失败");
  }
}

async function keepTopCandidates() {
  try {
    const result = await request("/source-candidates/keep-top-official?top=3", { method: "POST" });
    setHtml("sourceDiagnosticsReport", jsonBlock(result));
    showSuccess("每校 Top3 候选保留完成");
    await loadSourceCandidates();
  } catch (error) {
    showMessage(error.message || "Top3 处理失败");
  }
}

async function candidateAction(action, id) {
  try {
    if (action === "approve") {
      const result = await request(`/source-candidates/${id}/approve`, { method: "POST" });
      showSuccess(result.message || "候选源已确认启用");
      await Promise.allSettled([loadSourceCandidates(), loadSources()]);
      return;
    }
    if (action === "reject") {
      const result = await request(`/source-candidates/${id}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason: "管理员人工驳回" })
      });
      showSuccess(result.message || "候选源已驳回");
      await loadSourceCandidates();
      return;
    }
    if (action === "check") {
      await sourceAction("check-source", id);
      return;
    }
    if (action === "preview") {
      await sourceAction("preview-source", id);
    }
  } catch (error) {
    showMessage(error.message || "候选源操作失败");
  }
}

function bindEvents() {
  $("sourceForm")?.addEventListener("submit", saveSource);
  $("fillMappingBtn")?.addEventListener("click", () => {
    if ($("fieldMappingJson")) $("fieldMappingJson").value = JSON.stringify(CHINESE_FIELD_MAPPING, null, 2);
  });
  $("fillParserConfigBtn")?.addEventListener("click", () => {
    if ($("parserConfigJson")) $("parserConfigJson").value = JSON.stringify(HTML_PARSER_CONFIG, null, 2);
  });
  $("resetSourceFormBtn")?.addEventListener("click", resetSourceForm);
  $("refreshSourcesBtn")?.addEventListener("click", loadSources);
  $("runCollectorsBtn")?.addEventListener("click", runCollectors);
  $("bulkExtractFileLinksBtn")?.addEventListener("click", bulkExtractFileLinks);
  $("refreshRunsBtn")?.addEventListener("click", loadCollectorRuns);
  $("verifyRecordBtn")?.addEventListener("click", verifySelectedRecord);
  $("rejectRecordBtn")?.addEventListener("click", rejectSelectedRecord);
  $("generateCoverageBtn")?.addEventListener("click", generateCoverageReport);
  $("generateGapBtn")?.addEventListener("click", generateGapDiagnosisReport);
  $("backfillSourcesBtn")?.addEventListener("click", backfillSourceSchoolNames);
  $("diagnoseSourcesBtn")?.addEventListener("click", diagnoseSourcesWithoutRecords);
  $("actionQueueBtn")?.addEventListener("click", generateSourceActionQueue);
  $("deepSearchMissingBtn")?.addEventListener("click", deepSearchMissingSources);
  $("filterOfficialCandidatesBtn")?.addEventListener("click", filterOfficialCandidates);
  $("keepTopCandidatesBtn")?.addEventListener("click", keepTopCandidates);
  $("refreshCandidatesBtn")?.addEventListener("click", () => loadSourceCandidates(candidateIncludeAll));
  $("officialOnlyCandidatesBtn")?.addEventListener("click", () => {
    candidateIncludeAll = false;
    $("officialOnlyCandidatesBtn")?.classList.add("active");
    $("includeAllCandidatesBtn")?.classList.remove("active");
    loadSourceCandidates(false);
  });
  $("includeAllCandidatesBtn")?.addEventListener("click", () => {
    candidateIncludeAll = true;
    $("includeAllCandidatesBtn")?.classList.add("active");
    $("officialOnlyCandidatesBtn")?.classList.remove("active");
    loadSourceCandidates(true);
  });
  $("refreshAllBtn")?.addEventListener("click", initPage);

  $("sourceList")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    sourceAction(button.dataset.action, button.dataset.id);
  });

  $("rawRecordList")?.addEventListener("click", (event) => {
    const card = event.target.closest("[data-id]");
    if (card) loadRawRecordDetail(card.dataset.id);
  });

  $("sourceCandidatesList")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-candidate-action]");
    if (!button) return;
    candidateAction(button.dataset.candidateAction, button.dataset.id);
  });

  document.querySelectorAll(".btn-filter[data-status]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".btn-filter[data-status]").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      selectedRecordId = null;
      setRecordButtons(false);
      setHtml("rawRecordDetail", '<div class="empty">请选择左侧记录。</div>');
      loadRawRecords(button.dataset.status || "");
    });
  });
}

async function initPage() {
  showMessage("");
  await Promise.allSettled([
    safeRun(loadSources, "加载数据源"),
    safeRun(loadCollectorRuns, "加载采集记录"),
    safeRun(() => loadRawRecords(currentRawStatus), "加载 raw 数据"),
    safeRun(loadLatestReports, "加载报告"),
    safeRun(() => loadSourceCandidates(candidateIncludeAll), "加载候选源")
  ]);
}

window.addEventListener("error", (event) => {
  console.error("全局错误", event.error || event.message);
  showMessage(`页面脚本错误：${event.message || event.error}`);
});

window.addEventListener("unhandledrejection", (event) => {
  console.error("未处理 Promise 错误", event.reason);
  const reason = event.reason && event.reason.message ? event.reason.message : event.reason;
  showMessage(`异步请求错误：${reason}`);
});

document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  initPage();
});
