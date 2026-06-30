/**
 * node_proxy_setup.mjs — 让 Node.js 原生 fetch() 走系统代理
 *
 * Node.js 的 undici fetch 不会自动读取 HTTP_PROXY/HTTPS_PROXY 环境变量。
 * 此脚本在 Node 启动时通过 NODE_OPTIONS=--import 注入，
 * 读取代理环境变量并设置 undici 全局 dispatcher。
 *
 * 用法: $env:NODE_OPTIONS = "--import=path/to/node_proxy_setup.mjs"
 */

import { ProxyAgent, setGlobalDispatcher } from 'undici';

const proxyUrl =
  process.env.HTTPS_PROXY ||
  process.env.https_proxy ||
  process.env.HTTP_PROXY ||
  process.env.http_proxy;

if (proxyUrl) {
  try {
    const agent = new ProxyAgent({
      uri: proxyUrl,
      keepAliveTimeout: 10_000,
      keepAliveMaxTimeout: 10_000,
    });
    setGlobalDispatcher(agent);
    // 仅输出到 stderr，不影响 stdout 的 JSON 解析
    process.stderr.write(`[node-proxy] undici global dispatcher → ${proxyUrl}\n`);
  } catch (e) {
    process.stderr.write(`[node-proxy] WARNING: failed to set proxy: ${e.message}\n`);
  }
} else {
  process.stderr.write('[node-proxy] no proxy env vars set, using direct connection\n');
}
