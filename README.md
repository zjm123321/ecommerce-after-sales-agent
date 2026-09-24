# 电商售后 Agent 最小原型

当前版本只完成一条业务链路：输入有效订单和物流问题，返回物流催办。

## 工作流

```text
用户输入
  → classify_issue 识别物流问题
  → load_order 查询模拟订单
  → generate_resolution 生成物流催办结果
```

## 安装

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 运行

```powershell
python -m app.main
```

可使用：

```text
订单号：ORD-1001
问题：我的物流晚了三天还没到
```

## 测试

```powershell
python -m pytest -q
```
