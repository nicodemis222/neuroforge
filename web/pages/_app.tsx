import type { AppProps } from "next/app";
import { useEffect, useState } from "react";
import InitScreen from "../components/InitScreen";

export default function App({ Component, pageProps }: AppProps) {
  const [ready, setReady] = useState<boolean | null>(null);

  useEffect(() => {
    fetch("/api/init/status")
      .then(r => r.json())
      .then(d => setReady(!!d.ready))
      .catch(() => setReady(false));
  }, []);

  if (ready === null) {
    return (
      <div style={{ background: "#0a0e14", color: "#7fe", height: "100vh",
                    display: "grid", placeItems: "center",
                    fontFamily: "ui-monospace,Menlo,monospace" }}>
        contacting api…
      </div>
    );
  }
  if (ready === false) {
    return <InitScreen onReady={() => setReady(true)} />;
  }
  return <Component {...pageProps} />;
}
