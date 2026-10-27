from http.cookies import SimpleCookie
from io import BytesIO
from urllib.parse import urlsplit
from openpyxl import Workbook
import requests
import json

cloudUrl = "https://cloud.tsinghua.edu.cn"

class CloudPuller:
    def __init__(self, cookie):
        self.session = requests.session()
        parsed_cookie = SimpleCookie()
        parsed_cookie.load(cookie)
        if not parsed_cookie:
            raise ValueError("Cookie 为空或格式不正确，请复制完整的 Cookie 请求头值。")
        for name, item in parsed_cookie.items():
            self.session.cookies.set(
                name, item.value, domain=urlsplit(cloudUrl).hostname,
                path="/", secure=True,
            )
        ret1 = self.session.get(cloudUrl, timeout=30)
        if ret1.status_code != 200 or urlsplit(ret1.url).netloc != urlsplit(cloudUrl).netloc:
            raise RuntimeError("无法访问云盘，请重新登录浏览器并更新 Cookie。")
        print("[CloudPuller] Cookie 已加载，已连接云盘；添加成员仍需群组管理权限。")


    def pull(self, group_id, user_id):
        """按学号、完整联系邮箱或完整内部 ID 导入一名成员。"""
        identifier = str(user_id).strip() if user_id is not None else ""
        if not identifier:
            raise ValueError("成员标识不能为空，请填写学号、完整学校邮箱或完整内部 ID。")

        # 导入接口依次匹配内部 ID、contact_email、login_id；不要给学号拼接后缀。
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["Email"])
        cell = sheet.cell(row=2, column=1, value=identifier)
        cell.data_type = "s"
        with BytesIO() as stream:
            workbook.save(stream)
            workbook_bytes = stream.getvalue()
        workbook.close()

        print(f"[CloudPuller] 按原始标识导入：{identifier}")
        ret4 = self.session.post(cloudUrl + f"/api/v2.1/groups/{group_id}/members/import/",
                                 files={"file": (
                                     "members.xlsx", workbook_bytes,
                                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                 )},
                                 headers={'referer': f"https://cloud.tsinghua.edu.cn/group/{group_id}/",
                                          'x-csrftoken': self.session.cookies.get("sfcsrftoken"),
                                          'Accept-Language': 'en'},
                                 timeout=30, allow_redirects=False)
        if ret4.status_code != 200:
            try:
                error = ret4.json()
            except ValueError:
                error = {}
            detail = (error.get("error_msg") or error.get("detail") or ret4.reason) if isinstance(error, dict) else ret4.reason
            hint = ""
            if ret4.status_code == 403 and detail == "Permission denied.":
                hint = " 当前账号没有添加成员的权限，请让目标群组的群主将该账号设为管理员。"
            elif ret4.status_code in (301, 302, 303, 307, 308, 401):
                hint = " 请重新登录浏览器并更新 Cookie。"
            elif ret4.status_code == 404:
                hint = " 请核对群组 ID，以及当前云盘是否开放成员导入接口。"
            raise RuntimeError(f"添加成员失败（HTTP {ret4.status_code}）：{detail}{hint}")

        try:
            res = ret4.json()
        except ValueError as exc:
            raise RuntimeError("成员导入接口未返回 JSON，请检查登录状态和接口地址。") from exc
        if not isinstance(res, dict) or not isinstance(res.get("success"), list) or not isinstance(res.get("failed"), list):
            raise RuntimeError("成员导入接口返回格式异常，未确认添加结果。")
        successes, failures = res["success"], res["failed"]
        if len(successes) == 1 and not failures and isinstance(successes[0], dict):
            member = successes[0]
            username = member.get("name") or member.get("email") or identifier
            print(
                f"\033[0;32m[CloudPuller] [Success] User {username} is pulled into Group#{group_id}.\033[0m")
            return True
        if successes or len(failures) != 1 or not isinstance(failures[0], dict):
            raise RuntimeError("成员导入接口返回数量异常，未确认添加结果。")
        failure = failures[0]
        reason = failure.get("error_msg")
        if not isinstance(reason, str):
            raise RuntimeError("成员导入失败，但服务器未提供有效的错误信息。")
        username = failure.get("email_name") or failure.get("email") or identifier
        if reason.endswith("not found."):
            print(
                f"\033[0;33m[CloudPuller] [Failure] 未匹配到账号 {identifier}。"
                f"服务器返回：{reason}\033[0m")
            return False
        if reason.endswith('already a group member.'):
            print(
                f"\033[0;32m[CloudPuller] [Success] User {username} is already a member of Group#{group_id}.\033[0m")
            return True
        raise RuntimeError(f"添加成员 {identifier} 失败：{reason}")
    
    def delete(self, group_id, user_id):
        email = user_id + "@tsinghua.edu.cn" if (user_id[0] == '2' and len(
            user_id) == 10) else user_id + "@mails.tsinghua.edu.cn"
        print(email)
        ret4 = self.session.delete(cloudUrl + f"/api/v2.1/groups/{group_id}/members/{email}/",
                                   headers={'referer': f"https://cloud.tsinghua.edu.cn/group/{group_id}/",
                                          'x-csrftoken': self.session.cookies.get("sfcsrftoken")})
        res = json.loads(ret4.text)
        
        if ret4.status_code == 200:
            if res["success"]:
                print(
                    f"\033[0;32m[CloudPuller] [Success] User {user_id} is deleted from Group#{group_id}.\033[0m")
                return True
            else:
                assert False
        
        if ret4.status_code == 400:
            reason = res["error_msg"]
            print(
                f"\033[0;31m[CloudPuller] [ERROR] Failed to delete User {user_id} from Group#{group_id}, reason: {reason}\033[0m")
            return False
        
        if ret4.status_code == 403:
            reason = res["error_msg"]
            print(
                f"\033[0;31m[CloudPuller] [ERROR] Failed to delete User {user_id} from Group#{group_id}, reason: {reason}\033[0m")
            return False

        assert False
