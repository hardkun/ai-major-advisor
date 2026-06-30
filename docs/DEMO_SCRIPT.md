# 面试演示脚本

## 1. 启动后端

```bash
python -m uvicorn main:app --reload
```

打开健康检查：

```text
http://127.0.0.1:8000/health
```

## 2. 打开 Swagger

```text
http://127.0.0.1:8000/docs
```

可以先展示：

- `POST /recommend`
- `GET /reports/{report_id}`
- `GET /raw-data-sources`
- `GET /raw-admission-records`
- `GET /collector-runs`

## 3. 打开 admin 后台

```text
http://127.0.0.1:8000/admin
```

建议演示顺序：

1. 查看数据源列表 raw_data_sources。
2. 查看采集日志 collector_runs。
3. 查看覆盖率报告和缺口诊断。
4. 查看 raw 数据列表。
5. 打开一条 raw 数据详情，说明“自动采集不会直接进入推荐库”。
6. 演示核验通过后写入 admissions。

## 4. 演示 recommend 接口

请求示例：

```json
{
  "province": "四川",
  "score": 603,
  "rank": 22000,
  "subject_type": "物理类",
  "target_direction": "AI算法",
  "use_ai": true
}
```

重点解释返回字段：

- `school_name`
- `major_name`
- `match_type`
- `min_score`
- `min_rank`
- `source_name`
- `is_verified`
- `ai_explanation`
- `disclaimer`

## 5. 演示微信小程序

1. 打开微信开发者工具。
2. 进入首页，输入分数、位次、科类和目标方向。
3. 查看推荐结果页。
4. 查看报告页。
5. 演示 6 元完整报告的 mock-pay 解锁流程。

## 6. 推荐讲解重点

这个项目不是让 AI 直接“拍脑袋推荐学校”。推荐排序由规则算法和已核验数据决定，AI 只负责解释推荐结果、专业学习内容、就业方向和风险提示。

这套设计更适合高责任场景：数据可追溯、规则可解释、AI 输出有边界。
