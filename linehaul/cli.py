#!/usr/bin/env python3.5
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import logging.config

import click
import prometheus_client
import raven

from . import _tls as tls
from ._click import AsyncCommand
from ._server import Server
from .bigquery import BigQueryClient
from .core import Linehaul


__version__ = raven.fetch_package_version("linehaul")


@click.command(
    cls=AsyncCommand,
    context_settings={"auto_envvar_prefix": "LINEHAUL"},
)
@click.option("--bind", default="0.0.0.0")
@click.option("--port", type=int, default=512)
@click.option("--token")
@click.option("--account")
@click.option("--key", type=click.File("r"))
@click.option("--reuse-port/--no-reuse-port", default=True)
@click.option(
    "--tls-ciphers",
    default="ECDHE+CHACHA20:ECDH+AES128GCM:ECDH+AES128:!SHA:!aNULL:!eNULL",
)
@click.option(
    "--tls-certificate",
    type=click.Path(
        exists=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
)
@click.option("--metrics-port", type=int, default=12000)
@click.option("--sentry-dsn")
@click.option("--log-file")
@click.argument("table", envvar="BIGQUERY_TABLE")
@click.pass_context
async def main(ctx, bind, port, token, account, key, reuse_port, tls_ciphers,
               tls_certificate, metrics_port, sentry_dsn, log_file, table):
    # Configure logging
    target_logger = "logfile" if log_file else "console"
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,

        "formatters": {
            "console": {
                "format": "[%(asctime)s][%(levelname)s] %(name)s "
                          "%(filename)s:%(funcName)s:%(lineno)d | %(message)s",
                "datefmt": "%H:%M:%S",
            },
        },

        "handlers": {
            "console": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "console",
            },
            "logfile": {
                "level": "DEBUG",
                "class": "logging.handlers.WatchedFileHandler",
                "formatter": "console",
                "filename": log_file or "/dev/null",
            },
            "sentry": {
                "level": "ERROR",
                "class": "raven.handlers.logging.SentryHandler",
                "dsn": sentry_dsn,
                "release": __version__,
            },
        },

        "loggers": {
            "": {
                "handlers": [target_logger, "sentry"],
                "level": "DEBUG",
                "propagate": False,
            },
            "linehaul.user_agents": {
                "handlers": [target_logger],
                "level": "DEBUG",
                "propagate": False,
            },
        },
    })

    # Start up our metrics server in another thread.
    prometheus_client.start_http_server(metrics_port)

    bqc = BigQueryClient(*table.split(":"), client_id=account, key=key.read())

    if tls_certificate is not None:
        ssl_context = tls.create_context(tls_certificate, tls_ciphers)
    else:
        ssl_context = None

    with Linehaul(token=token, bigquery=bqc, loop=ctx.event_loop) as lh:
        async with Server(lh, bind, port,
                          reuse_port=reuse_port,
                          ssl=ssl_context,
                          loop=ctx.event_loop) as s:
            try:
                await s.wait_closed()
            except asyncio.CancelledError:
                click.echo(click.style("Shutting Down...", fg="yellow"))
