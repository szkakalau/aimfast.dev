"use client";

import { useEffect } from "react";

export default function Home() {
  useEffect(() => {
    window.location.replace("/dashboard/");
  }, []);

  return (
    <html lang="zh-CN">
      <head>
        <meta httpEquiv="refresh" content="0;url=/dashboard/" />
        <title>KAKAOPC — Builder Workbench</title>
      </head>
      <body style={{ background: "#1a1d24", color: "#fff", fontFamily: "system-ui", display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", margin: 0 }}>
        <p>Redirecting to <a href="/dashboard/" style={{ color: "#f59e42" }}>Builder Workbench</a>...</p>
      </body>
    </html>
  );
}
