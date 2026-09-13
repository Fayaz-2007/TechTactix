import { useEffect, useRef, useState } from "react";
import { getMonitorStatus } from "../../api/client";
import "./NetworkMonitor.css";

const POLL_INTERVAL_MS = 2000;

/**
 * Polls GET /api/monitor every 2s and shows a compact clean/alert badge.
 */
function NetworkMonitor() {
  const [status, setStatus] = useState(null);
  const [unreachable, setUnreachable] = useState(false);
  const timerRef = useRef(null);

  useEffect(() => {
    let isMounted = true;

    const poll = async () => {
      try {
        const data = await getMonitorStatus();
        if (!isMounted) return;
        setStatus(data);
        setUnreachable(false);
      } catch {
        if (!isMounted) return;
        setUnreachable(true);
      }
    };

    poll();
    timerRef.current = setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      isMounted = false;
      clearInterval(timerRef.current);
    };
  }, []);

  if (unreachable) {
    return (
      <div className="network-monitor network-monitor--unknown">
        <span className="network-monitor__dot" />
        Monitor unreachable
      </div>
    );
  }

  if (!status) {
    return (
      <div className="network-monitor network-monitor--unknown">
        <span className="network-monitor__dot" />
        Checking network&hellip;
      </div>
    );
  }

  const externalCount = status.external_connections ?? 0;
  const isClean = status.status === "clean" && externalCount === 0;

  return (
    <div className={"network-monitor " + (isClean ? "network-monitor--clean" : "network-monitor--alert")}>
      <span className="network-monitor__dot" />
      {isClean ? (
        <span>0 external connections — fully offline</span>
      ) : (
        <span>
          {externalCount} external connection{externalCount === 1 ? "" : "s"} detected
          {typeof status.local_connections === "number" && ` · ${status.local_connections} local`}
        </span>
      )}
    </div>
  );
}

export default NetworkMonitor;
