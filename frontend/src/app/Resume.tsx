import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { getRoadmap } from "@/lib/api";
import { clearStudentId, getStudentId } from "@/lib/identity";

// The root route. Resolves where a fresh load should land: no stored id -> Setup;
// a stored id with a live analysis -> Roadmap; a stored id whose analysis is gone
// (e.g. a re-onboarded student on another device) -> clear it and fall back to Setup.
export function Resume() {
  const navigate = useNavigate();

  useEffect(() => {
    if (!getStudentId()) {
      navigate("/setup", { replace: true });
      return;
    }
    getRoadmap()
      .then(() => navigate("/roadmap", { replace: true }))
      .catch(() => {
        clearStudentId();
        navigate("/setup", { replace: true });
      });
  }, [navigate]);

  return <div className="p-8 text-muted-foreground">Loading…</div>;
}
