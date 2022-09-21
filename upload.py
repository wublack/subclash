'''
Author: Wu
Date: 2022-09-21 17:09:06
LastEditors: Wu
LastEditTime: 2022-09-21 17:10:43
Description: 
'''
import os
import time
import pygit2 as git

import locale
locale.setlocale(locale.LC_CTYPE, 'chinese')

def red(str: str):
    return '\x1b[31m{:s}\x1b[0m'.format(str)


def green(str: str):
    return '\x1b[32m{:s}\x1b[0m'.format(str)


def yellow(str: str):
    return '\x1b[33m{:s}\x1b[0m'.format(str)


def blue(str: str):
    return '\x1b[96m{:s}\x1b[0m'.format(str)


def gray(str: str):
    return '\x1b[90m{:s}\x1b[0m'.format(str)

def get_config(repo: git.Repository, key: str):
    try:
        val: str = repo.config.__getitem__(key)
        return val
    except:
        print('获取配置[{:s}]失败，请通过以下命令配置：'.format(key))
        print('git config --global {:s}=[...]'.format(key))
        return None

username = get_config(repo, 'user.name')
# git config user.name
def git_add_all(repo: git.Repository):
    """
    git add .
    """
    try:
        idx = repo.index
        idx.add_all()
        idx.write()
    except Exception as e:
        print(e)
        return False

    return True
def git_commit(repo: git.Repository, msg: str, username: str, useremail: str):
    """
    git commit -m "msg"
    """
    try:
        author = git.Signature(username, useremail)
        committer = author
        tree = repo.index.write_tree()
        parents = [] if repo.head_is_unborn else [repo.head.target]
        ref = 'HEAD' if repo.head_is_unborn else repo.head.name
        hash: str = repo.create_commit(
            ref, author, committer, msg, tree, parents)
        return hash
    except Exception as e:
        print('git_commit(): ', e)
        return None
def get_current_branch(repo: git.Repository):
    for name in repo.branches.local:
        branch = repo.lookup_branch(name)
        if branch.is_head():
            bName: str = branch.branch_name
            return bName
    return None

if __name__ == '__main__':
    # 读取仓库信息
    repo_path = os.getcwd()
    try:
        repo = git.Repository(repo_path)
    except:
        print(red('[{:s}]不是一个git仓库').format(repo_path))
        exit()

    # 检查是否发生更改，决定是否进行提交操作
    status = [item for item in repo.status().items() if item[1] != 16384]
    if len(list(status)) == 0:
        print(yellow('仓库[{:s}]未发生更改').format(repo_path))
    else:
        # 获取文件更改信息
        create_items = []
        modify_items = []
        delete_items = []
        for item in status:
            if item[1] == 128:  # 新增
                create_items.append(item[0])
            elif item[1] == 256:  # 修改
                modify_items.append(item[0])
            elif item[1] == 512:  # 删除
                delete_items.append(item[0])

        # 获取提交者信息
        username = get_config(repo, 'user.name')
        useremail = get_config(repo, 'user.email')
        if username is None or useremail is None:
            exit()

        # 打印文件更改信息与提交者信息
        for item in create_items:
            print(green('create: [{:s}]').format(item))
        for item in modify_items:
            print(yellow('modify: [{:s}]').format(item))
        for item in delete_items:
            print(red('delete: [{:s}]').format(item))

        print('\nAuthor: {:s}[{:s}]'.format(gray(username), gray(useremail)))

        # 构建提交信息
        while True:
            print(yellow('\n请输入commit信息（为空则自动填充时间）'))
            msg = input()
            msg = time.strftime('%Y年%m月%d日 %H:%M:%S', time.localtime(
                time.time())) if msg == '' else msg

            if len(msg) > 50:
                print(gray('消息过长，请控制在50以内：'))
                print(msg[0:50])
                continue
            break

        # 提交 https://www.pygit2.org/recipes/git-commit.html
        if not git_add_all(repo):
            exit()
        hash = git_commit(repo, msg, username, useremail)
        if hash is None:
            print(red('提交失败！'))
            exit()

        # 打印提交的信息
        print(green('\n**********执行 commit 成功! **********'))
        commit = repo[hash]

        hash = blue(str(commit.id)[0:10] + '...')
        time = yellow(time.strftime('%Y年%m月%d日 %H:%M:%S',
                      time.localtime(commit.commit_time)))
        name = commit.author.name
        email = commit.author.email

        diff = repo.diff(commit.id, commit.parent_ids[0] if len(
            commit.parent_ids) > 0 else '4b825dc642cb6eb9a060e54bf8d69288fbee4904')
        new_lines = 0
        rmv_lines = 0
        files_changed = [[], [], []]
        for patch in diff:
            # ([更改的行的前后留白位置], [删除的行数], [新增的行数])
            line_stat = patch.line_stats
            new_lines += line_stat[2]
            rmv_lines += line_stat[1]

            line_modi = '{:s} {:s}'.format(green('+{:d}'.format(line_stat[2])), red(
                '-{:d}'.format(line_stat[1]))) if patch.delta.is_binary == False else ''

            if patch.delta.status == 2:  # create
                files_changed[0].append('* {type} {file} {line_modi}'.format(
                    file=gray(patch.delta.new_file.path),
                    type=green('create'),
                    line_modi=line_modi)
                )
            elif patch.delta.status == 1:  # delete
                files_changed[2].append('* {type} {file} {line_modi}'.format(
                    file=gray(patch.delta.new_file.path),
                    type=red('delete'),
                    line_modi=line_modi)
                )
            else:  # modify and other
                files_changed[1].append('* {type} {file} {line_modi}'.format(
                    file=gray(patch.delta.new_file.path),
                    type=yellow('modify'),
                    line_modi=line_modi)
                )

        files_changed = files_changed[0] + files_changed[1] + files_changed[2]

        msg = commit.message.replace('\n', '')
        print(
            '{hash} {time} {author} {new_lines} {rmv_lines} {msg}'.format(
                hash=hash, time=time, msg=msg,
                author=gray('{name}[{email}]'.format(name=name, email=email)),
                new_lines=green('+{:d}'.format(new_lines)),
                rmv_lines=red('-{:d}'.format(rmv_lines)),
            )
        )
        for item in files_changed:
            print(item)

    print(green('\n**********开始push到远程仓库**********'))

    # 检查远程仓库列表
    if len(repo.remotes) == 0:
        print(gray("远程仓库列表为空，无需push"))
        exit()
    else:
        # 当前分支
        cur_branch = get_current_branch(repo)
        if cur_branch is None:
            print(red('分支读取出错，请通过git检查'))
            exit()
        print('Current Branch: [{:s}]'.format(blue(cur_branch)))

        for remote in repo.remotes:
            try:
                print('\n正在推送远程仓库[{:s}]: {:s}'.format(
                    blue(remote.name), green(remote.url)))
                # remote.push([repo.head.name])  # 不支持ssh，懒得搞了，草
                os.system('git push {:s} {:s}'.format(remote.name, cur_branch))
                print(yellow('ok'))
            except Exception as e:
                print(gray('失败: {:s}').format(red(str(e))))
                exit()