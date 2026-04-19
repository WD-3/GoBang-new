#!/usr/bin/env python
"""
测试 Temperature 是否生效
Test if Temperature parameter is working
"""

from gobang.llm_player import OllamaClient, create_llm_player
from gobang.core import Stone


def test_ollama_temperature():
    """测试 Ollama temperature 是否生效"""
    print("=" * 60)
    print("Testing Ollama Temperature")
    print("=" * 60)

    # 创建两个相同模型的客户端，不同 temperature
    client1 = OllamaClient(model="gemma3:1b", temperature=0.1)
    client2 = OllamaClient(model="gemma3:1b", temperature=0.9)

    prompt = "1+1=? Answer with one number only:"

    print(f"\nPrompt: {prompt}")
    print(f"\nClient 1 (temp=0.1):")
    try:
        resp1 = client1.generate(prompt)
        print(f"Response 1: {resp1}")
    except Exception as e:
        print(f"Error: {e}")

    print(f"\nClient 2 (temp=0.9):")
    try:
        resp2 = client2.generate(prompt)
        print(f"Response 2: {resp2}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 60)
    print("如果两次响应相同，说明 Temperature 可能无效")
    print("If responses are same, Temperature may not be working")
    print("=" * 60)


def test_same_prompt_multiple_times():
    """同一 prompt 多次调用，看响应是否相同"""
    print("\n" + "=" * 60)
    print("Testing Same Prompt Multiple Times")
    print("=" * 60)

    client = OllamaClient(model="gemma3:1b", temperature=0.5)

    prompt = "五子棋棋盘 13x13，黑方 H8，白方 H7，黑方 H6，白方 G6，黑方 I6，现在轮到白方。请输出下一步坐标，只输出如 H8："

    print(f"\nPrompt: {prompt[:80]}...")

    for i in range(5):
        try:
            resp = client.generate(prompt)
            print(f"Response {i + 1}: {resp.strip()}")
        except Exception as e:
            print(f"Error {i + 1}: {e}")

    print("\n" + "=" * 60)
    print("如果 5 次响应都相同，说明 Temperature=0.5 时仍然确定性输出")
    print("If all 5 responses are same, Temperature=0.5 still gives deterministic output")
    print("=" * 60)


if __name__ == "__main__":
    # 检查 Ollama 是否可用
    from gobang.llm_player import check_ollama_available

    if not check_ollama_available():
        print("❌ Ollama 服务不可用！请先启动 Ollama")
        print("❌ Ollama service not available! Please start Ollama first")
        exit(1)

    print("✓ Ollama 服务可用")

    # 运行测试
    test_ollama_temperature()
    test_same_prompt_multiple_times()
