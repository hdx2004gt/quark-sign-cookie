"""
夸克网盘自动签到 - Cookie 版（网页版）
支持 GitHub Actions 自动执行
"""

import os
import re
import sys
import json
import requests


def get_env():
    """获取环境变量"""
    if "COOKIE_QUARK" in os.environ:
        cookie_list = re.split(r'\n|&&', os.environ.get('COOKIE_QUARK'))
        return [c.strip() for c in cookie_list if c.strip()]
    print('❌ 未添加 COOKIE_QUARK 变量')
    sys.exit(0)


def convert_bytes(b):
    """将字节转换为可读格式"""
    units = ("B", "KB", "MB", "GB", "TB", "PB")
    i = 0
    while b >= 1024 and i < len(units) - 1:
        b /= 1024
        i += 1
    return f"{b:.2f} {units[i]}"


class QuarkWebSign:
    """夸克网盘网页版签到类"""

    def __init__(self, cookie_str, user_name="未知用户"):
        self.cookie_str = cookie_str
        self.user_name = user_name
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://pan.quark.cn/',
            'Origin': 'https://pan.quark.cn',
        })
        self.session.headers['Cookie'] = cookie_str

    def get_growth_info(self):
        """获取签到信息"""
        urls_to_try = [
            "https://pan.quark.cn/api/user/info",
            "https://pan.quark.cn/cloudapi/ucp/capacity/growth/info",
            "https://drive-m.quark.cn/1/clouddrive/capacity/growth/info",
        ]
        for url in urls_to_try:
            try:
                resp = self.session.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("data"):
                        return data["data"]
                    elif data.get("result"):
                        return data
            except Exception:
                continue
        return None

    def sign_with_cookie(self):
        """使用 Cookie 执行签到"""
        log_lines = []
        log_lines.append(f"🙍🏻‍♂️ 用户: {self.user_name}")

        sign_apis = [
            {"url": "https://drive-m.quark.cn/1/clouddrive/capacity/growth/sign",
             "method": "post", "params": {"pr": "ucpro", "fr": "pc"},
             "data": {"sign_cyclic": True}, "desc": "移动端签到 API"},
            {"url": "https://pan.quark.cn/cloudapi/ucp/capacity/growth/sign",
             "method": "post", "params": {}, "data": {}, "desc": "网页版签到 API"},
        ]

        log_lines.append("📊 正在查询签到状态...")
        info = self.get_growth_info()

        if info:
            try:
                cap_sign = info.get("cap_sign", info)
                total_cap = info.get("total_capacity", 0)
                log_lines.append(f"💾 总容量: {convert_bytes(total_cap)}")
                if isinstance(cap_sign, dict):
                    signed = cap_sign.get("sign_daily", False)
                    progress = cap_sign.get("sign_progress", 0)
                    target = cap_sign.get("sign_target", 0)
                    reward = cap_sign.get("sign_daily_reward", 0)
                    if signed:
                        log_lines.append(f"✅ 今日已签到 +{convert_bytes(reward)}, 进度 ({progress}/{target})")
                        return "\n".join(log_lines)
                    else:
                        log_lines.append(f"⏳ 今日未签到, 进度 ({progress}/{target})")
            except Exception as e:
                log_lines.append(f"⚠️ 解析异常: {e}")
        else:
            log_lines.append("⚠️ 无法获取签到信息，尝试直接签到...")

        for api in sign_apis:
            try:
                log_lines.append(f"🔄 尝试: {api['desc']}")
                if api['method'] == 'post':
                    resp = self.session.post(api['url'], params=api['params'], json=api['data'], timeout=10)
                else:
                    resp = self.session.get(api['url'], params=api['params'], timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("data"):
                        reward = data["data"].get("sign_daily_reward", 0)
                        log_lines.append(f"✅ 签到成功! +{convert_bytes(reward)}")
                        return "\n".join(log_lines)
                    else:
                        log_lines.append(f"⚠️ 返回: {json.dumps(data, ensure_ascii=False)[:200]}")
                else:
                    log_lines.append(f"⚠️ HTTP {resp.status_code}: {resp.text[:100]}")
            except Exception as e:
                log_lines.append(f"❌ 失败: {e}")

        log_lines.append("\n💡 如果失败，建议用手机抓包获取 kps/sign/vcode")
        return "\n".join(log_lines)


def parse_cookie_user(cookie_str):
    match = re.search(r'__uid=([^;]+)', cookie_str)
    if match:
        return match.group(1)[:20] + "..."
    match = re.search(r'b-user-id=([^;]+)', cookie_str)
    if match:
        return match.group(1)[:12] + "..."
    return "用户"


def main():
    print("=" * 50)
    print("   夸克网盘自动签到 (Cookie 版)")
    print("=" * 50)

    cookie_list = get_env()
    print(f"✅ 检测到 {len(cookie_list)} 个账号\n")

    all_results = []
    for i, cookie_str in enumerate(cookie_list):
        user_data = {}
        for item in cookie_str.split(';'):
            item = item.strip()
            if '=' in item:
                key, val = item.split('=', 1)
                user_data[key.strip()] = val.strip()
        user_name = user_data.get('user', parse_cookie_user(cookie_str))
        print(f"--- 第 {i+1} 个账号 ---")
        signer = QuarkWebSign(cookie_str, user_name)
        result = signer.sign_with_cookie()
        print(result)
        print()
        all_results.append(result)

    print("=" * 50)
    print("   签到完成!")
    print("=" * 50)
    return "\n\n".join(all_results)


if __name__ == "__main__":
    main()
