# Efficiency Tracker

基于 [ActivityWatch](https://github.com/ActivityWatch/activitywatch) 的个人效率追踪系统，自动收集电脑使用数据并生成 AI 分析报告。

## 功能特点

- **自动数据采集**：从 ActivityWatch 获取窗口、AFK、浏览器、编辑器等事件数据
- **智能数据处理**：过滤 AFK 时间，按应用/类别/域名聚合统计
- **AI 分析报告**：调用 OpenAI 兼容 API 生成效率分析和改进建议
- **趋势对比**：日报对比昨天，周报对比上周，追踪效率变化
- **多周期支持**：支持日报、周报和自定义时间范围
- **定时任务**：支持自动定时生成报告（macOS launchd）
- **消息推送**：支持钉钉个人消息和邮件通知
- **Markdown 导出**：自动保存报告到本地文件

## 前置要求

- Python 3.9+
- [ActivityWatch](https://github.com/ActivityWatch/activitywatch) 已安装并运行
- OpenAI 兼容的 API（可选，用于 AI 分析）

## 安装

```bash
# 克隆项目
git clone <your-repo-url>
cd efficiency-tracker

# 安装依赖
pip install -r requirements.txt
```

## 快速开始

```bash
# 生成本周周报
python main.py

# 生成今日日报
python main.py --period day

# 跳过 AI 分析，仅查看统计数据
python main.py --no-ai

# 自定义时间范围
python main.py --start 2024-01-01 --end 2024-01-07
```

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--period` | 报告周期：`day`（日报）或 `week`（周报） | `week` |
| `--start` | 开始日期（格式：YYYY-MM-DD） | - |
| `--end` | 结束日期（格式：YYYY-MM-DD） | - |
| `--no-ai` | 跳过 AI 分析 | `false` |
| `--config` | 配置文件路径 | `config/config.yaml` |

## 配置

编辑 `config/config.yaml` 文件：

```yaml
# ActivityWatch 服务地址
activitywatch:
  host: "http://localhost:5600"

# AI API 配置
ai:
  api_base: "https://your-api-endpoint/v1"
  api_key: "your-api-key"
  model: "gpt-4"

# 应用分类规则
categories:
  coding:
    - "VS Code"
    - "PyCharm"
    - "Terminal"
  browser:
    - "Chrome"
    - "Safari"
  # ...
```

### 环境变量

AI 配置支持环境变量覆盖：

```bash
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_API_KEY="sk-xxx"
```

## 定时任务

自动在每天/每周固定时间生成报告：

```bash
# 安装定时任务（macOS）
python scripts/install_scheduler.py

# 卸载定时任务
python scripts/uninstall_scheduler.py
```

默认时间：
- 日报：每天 21:30
- 周报：每周日 21:30

## 消息推送

支持将报告推送到钉钉或邮箱。在 `config/config.yaml` 中配置：

```yaml
notification:
  enabled: true

  channels:
    # 钉钉个人消息（需要企业内部应用）
    dingtalk:
      enabled: true
      corp_id: "your-corp-id"
      app_key: "your-app-key"
      app_secret: "your-app-secret"
      agent_id: "your-agent-id"
      user_id: "your-user-id"

    # 邮件通知
    email:
      enabled: true
      smtp_host: "smtp.example.com"
      smtp_port: 465
      smtp_user: "your-email@example.com"
      smtp_password: "your-password"
      to_address: "recipient@example.com"
```

## 项目结构

```
efficiency-tracker/
├── main.py              # 入口文件
├── config/
│   └── config.yaml      # 配置文件
├── src/
│   ├── __init__.py      # 模块导出
│   ├── collector.py     # 数据采集（ActivityWatch API）
│   ├── processor.py     # 数据处理与聚合
│   ├── analyzer.py      # AI 分析
│   ├── compare.py       # 趋势对比
│   ├── notifier.py      # 消息推送（钉钉/邮件）
│   └── reporter.py      # 报告生成与输出
├── scripts/
│   ├── install_scheduler.py    # 安装定时任务
│   └── uninstall_scheduler.py  # 卸载定时任务
├── reports/             # 生成的报告目录
├── logs/                # 定时任务日志
├── pyproject.toml       # 项目配置
├── requirements.txt     # 依赖列表
└── README.md
```

## 输出示例

```
==================================================
🚀 个人效率感知系统
==================================================

📅 周报: 2024-01-08 ~ 2024-01-14

📊 正在采集数据...
   - Window: aw-watcher-window_hostname
   - AFK: aw-watcher-afk_hostname
   - Editors: 2 个

⚙️  正在处理数据...
   - 总时长: 45.2 小时
   - 活跃时长: 38.5 小时
   - 编程时长: 22.3 小时

🤖 正在调用 AI 分析...

💾 报告已保存: ./reports/report_周报_2024-01-14.md
```

## License

MIT
