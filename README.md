# 顶会论文自动抓取、LLM总结、推送

1. 自动抓取顶会论文

> 以ICLR 2024为例

```bash
python auto_download_papers.py
```

2. 将抓取到的PDF利用MinerU转换成Markdown格式

```bash
python pdf2markdown.py
```

3. 调用本地ollama对Markdown格式的论文进行总结

以llama3.1-70B为例

```bash
python call_llm_summaries.py
```

总结提示词（Prompt）可以在代码里面修改。

4. 将总结后的内容每日推送到[Cubox](https://help.cubox.pro/save/89d3/)

```bash
python push2cubox.py
```
