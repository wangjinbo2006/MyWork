from CloudPull import CloudPuller

from numpy import arange

targetGroupID = 46881

def save_list(li):
    with open("./list.txt", "w") as file:
        for i in li:
            file.write(str(i))
            file.write('\n')


def load_list():
    with open("./list.txt", "r") as file:
        li = []
        for line in file.readlines():
            li.append(line.strip())
    return li


try:
    print("载入拉人列表...")
    member_list = load_list()
except FileNotFoundError:
    # member_list = list(arange(2021013218, 2021013421 + 1)) \
    #             + list(arange(2022012220, 2022012408 + 1)) + list(arange(2022012748, 2022012761 + 1)) \
    #             + list(arange(2023012281, 2023012471 + 1)) \
    #             + list(arange(2024011914, 2024012079 + 1)) + list(arange(2024012082, 2024012113 + 1))
    member_list = list(arange(2026011714, 2026011906 + 1))
    member_list = list(map(str, member_list))
    print("未找到列表文件，已使用默认配置")
    # (2021013218, 2021013421)
    # (2022012220, 2022012408), (2022012748, 2022012761)
    # (2023012281, 2023012471)
    # (2024011914, 2024012079), (2024012082, 2024012113)

if len(member_list) == 0:
    print("列表为空，已无人可拉")
    exit()

print("开始登录云盘...")
p = CloudPuller(
    cookie='sfcsrftoken=nS8X5jHar7rVsvztlecJiPr6c3wqrLTr; seahub_auth="2024012103@tsinghua.edu.cn@806e51d8434fa18597a11165c627653562e1d31d"; sessionid=3nfxwxtk9w2kisj1ja4kxt977jx7ihmk; via_oauth=true; _ga_69YPS2LP7R=GS2.1.s1792035926$o3$g1$t1792035942$j44$l0$h0; _ga=GA1.1.219185498.1790662264'
)

# print(member_list)
flag = []
for member in member_list:
    if p.pull(targetGroupID, member):
        flag.append(member)

if len(flag):
    print("拉人结束，", len(flag), "人已经是群组成员！学号:", flag)
    for member in flag:
        member_list.remove(member)
    save_list(member_list)
    print("列表文件已更新！")
    exit()

print("拉人结束，没有新人。")
