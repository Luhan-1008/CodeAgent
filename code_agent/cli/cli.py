import argparse

from code_agent.cli.app import AppCMD
from code_agent.cli.run import RunCMD


def run_cmd():
    """CLI 总入口。

    小白阅读建议：
    1) 先看 ArgumentParser 如何注册子命令。
    2) 再看 parse_known_args 之后如何把命令分发给具体类。
    3) 最后跟进 `RunCMD.execute()`，就能进入核心执行链路。
    """
    parser = argparse.ArgumentParser(
        'ModelScope-agent Command Line tool',
        usage='ms-agent <command> [<args>]')

    # subparsers 相当于“命令路由器”：run/app 各自实现一套参数与执行逻辑。
    subparsers = parser.add_subparsers(
        help='ModelScope-agent commands helpers')

    RunCMD.define_args(subparsers)
    AppCMD.define_args(subparsers)

    # unknown args 会交给下游配置系统处理（兼容动态配置字段）。
    args, _ = parser.parse_known_args()

    if not hasattr(args, 'func'):
        parser.print_help()
        exit(1)

    # func 是各子命令通过 set_defaults(func=...) 注入的构造函数。
    cmd = args.func(args)
    cmd.execute()


if __name__ == '__main__':
    run_cmd()
