import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import api, { setAccessToken } from "@/services/api";

interface LoginResponse {
  access_token: string;
  user_id: string;
  username: string;
  display_name: string;
  locale: string;
}

export default function LoginPage(): JSX.Element {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { data } = await api.post<LoginResponse>("/auth/login", { username, password });
      setAccessToken(data.access_token);
      // Apply user locale preference
      if (data.locale && ["zh-TW", "en"].includes(data.locale)) {
        await i18n.changeLanguage(data.locale);
      }
      navigate("/");
    } catch {
      setError(t("auth.invalidCredentials"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "100vh",
        background: "#f5f5f5",
      }}
    >
      <form
        onSubmit={(e) => void handleSubmit(e)}
        style={{
          background: "#fff",
          padding: "2rem",
          borderRadius: "8px",
          minWidth: "320px",
          boxShadow: "0 2px 8px rgba(0,0,0,.12)",
        }}
        aria-label="DocERP Login"
      >
        <h1 style={{ marginBottom: "1.5rem", fontSize: "1.25rem" }}>DocERP</h1>

        {error && (
          <p role="alert" style={{ color: "#c0392b", marginBottom: "1rem" }}>
            {error}
          </p>
        )}

        <label htmlFor="username" style={{ display: "block", marginBottom: "0.25rem" }}>
          {t("auth.username")}
        </label>
        <input
          id="username"
          type="text"
          autoComplete="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          style={{ width: "100%", marginBottom: "1rem", padding: "0.5rem" }}
        />

        <label htmlFor="password" style={{ display: "block", marginBottom: "0.25rem" }}>
          {t("auth.password")}
        </label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          style={{ width: "100%", marginBottom: "1.5rem", padding: "0.5rem" }}
        />

        <button
          type="submit"
          disabled={loading}
          style={{
            width: "100%",
            padding: "0.625rem",
            background: "#1677ff",
            color: "#fff",
            border: "none",
            borderRadius: "4px",
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? t("common.loading") : t("auth.loginButton")}
        </button>
      </form>
    </main>
  );
}
