import type { AppProps } from "next/app";
import { useEffect, useState } from "react";
import InitScreen from "../components/InitScreen";
import "../styles/globals.css";

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
      <div style={{
        height: "100vh", display: "grid", placeItems: "center",
        color: "#7fe5d3",
      }}>
        contacting api…
      </div>
    );
  }
  if (ready === false) {
    return <InitScreen onReady={() => setReady(true)} />;
  }
  return <Component {...pageProps} />;
}
