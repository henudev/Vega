#!/usr/bin/env python3
"""
Vega-TTS 测试脚本
生成示例语音文件
"""

import asyncio
import edge_tts
from pathlib import Path

OUTPUT_DIR = "/Users/shu/Desktop/Vega-TTS-output"
Path(OUTPUT_DIR).mkdir(exist_ok=True)

TEST_TEXTS = [
    {
        'text': '你好，我是石家庄第一猛虾！这是 Vega-TTS 文本转语音服务的测试。',
        'voice': 'zh-CN-XiaoxiaoNeural',
        'filename': 'test_intro.mp3'
    },
    {
        'text': 'Vega-TTS 基于微软 Edge 在线文本转语音能力构建。',
        'voice': 'zh-CN-YunyangNeural',
        'filename': 'test_description.mp3'
    },
    {
        'text': '支持多种语言和声音，无需 API 密钥，免费使用。',
        'voice': 'zh-CN-XiaoyiNeural',
        'filename': 'test_features.mp3'
    }
]

async def generate_tts(text, voice, output_path):
    """生成语音"""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)
    print(f"✅ 已生成: {output_path}")
    print(f"   文本: {text}")

async def main():
    """生成所有测试语音"""
    print("🚀 开始生成测试语音...\n")
    
    tasks = []
    for test in TEST_TEXTS:
        output_path = Path(OUTPUT_DIR) / test['filename']
        tasks.append(generate_tts(test['text'], test['voice'], str(output_path)))
    
    await asyncio.gather(*tasks)
    
    print(f"\n✨ 全部完成！共生成 {len(TEST_TEXTS)} 个语音文件")
    print(f"📂 保存位置: {OUTPUT_DIR}")

if __name__ == '__main__':
    asyncio.run(main())
