"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  api,
  ApiError,
  type ApiRecord,
  type AssistantChatRequest,
} from "../lib/api";
import { useApp } from "./app-providers";
import { PageHeading } from "./availability";
import { AiAssistantIcon } from "./icons";
import { ApiStatus, isApiRecord, recordsFrom, textFrom } from "./analysis-data";
import { MarkdownMessage } from "./markdown-message";

type Turn = {
  role: "user" | "assistant";
  content: string;
  sources?: ApiRecord[];
  followups?: string[];
};

const guidedQuestions = [
  "What does the yield model predict for my selected location?",
  "Compare Rice and Bajra historically.",
  "Explain the recent rainfall pattern.",
  "What does High Concern mean?",
  "Why was HistGradientBoosting selected?",
];

function formatProvider(provider: string) {
  const clean = provider.toLowerCase().trim();
  if (clean === "openai") return "Cloud Language Model (OpenAI)";
  if (clean === "openai_compatible" || clean === "generic")
    return "Configured Cloud Language Model";
  if (!clean || clean === "not configured") return "Not configured";
  return provider;
}

export function AssistantPage() {
  const { t, language, capabilities } = useApp();
  const [status, setStatus] = useState<ApiRecord | null>(null);
  const [suggestions, setSuggestions] = useState<ApiRecord[]>([]);
  const [statusLoading, setStatusLoading] = useState(true);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [sending, setSending] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [location, setLocation] = useState({ state: "", district: "" });

  useEffect(() => {
    let active = true;
    Promise.allSettled([
      api.assistantStatus(),
      api.assistantSuggestions(),
    ]).then(([statusResult, suggestionResult]) => {
      if (!active) return;
      if (statusResult.status === "fulfilled") {
        setStatus(statusResult.value);
      } else {
        setStatusError("Assistant configuration status could not be loaded.");
      }
      if (suggestionResult.status === "fulfilled") {
        setSuggestions(normalizeSuggestions(suggestionResult.value));
      }
      setStatusLoading(false);
    });
    return () => {
      active = false;
    };
  }, []);

  const capability = capabilities.data?.capabilities.find(
    (item) => item.name === "grounded_assistant",
  );
  const serviceState = textFrom(
    status ?? {},
    ["status"],
    "unknown",
  ).toLowerCase();
  const configured = serviceState === "ready";
  const canChat =
    capability?.availability === "available" && configured && !statusLoading;
  const lastAssistantTurn = [...turns]
    .reverse()
    .find((turn) => turn.role === "assistant");
  const visibleSuggestions = useMemo(() => {
    const keys = language === "hi" ? ["hi", "en"] : ["en", "hi"];
    const mapped = suggestions
      .map((item) => textFrom(item, keys, ""))
      .filter((text) => text.trim().length > 0);
    return mapped.length ? mapped : guidedQuestions;
  }, [suggestions, language]);

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = draft.trim();
    if (!message || sending) return;
    setChatError(null);
    if (!canChat) {
      setChatError(
        "The assistant provider is not currently available. No response was generated.",
      );
      return;
    }
    const nextTurns = [...turns, { role: "user" as const, content: message }];
    setTurns(nextTurns);
    setDraft("");
    setSending(true);
    const request: AssistantChatRequest = {
      message,
      preferred_language: language,
      conversation_context: turns.slice(-6).map((turn) => ({
        role: turn.role,
        content: turn.content,
      })),
      ...(location.state || location.district
        ? { location_context: location }
        : {}),
    };
    try {
      const response = await api.assistantChat(request);
      const answer = typeof response.answer === "string" ? response.answer : "";
      if (!answer.trim()) {
        throw new ApiError("invalid-response");
      }
      const sources = recordsFrom(response.sources);
      const followups = stringList(response.suggested_followups);
      setTurns((current) => [
        ...current,
        {
          role: "assistant",
          content: answer,
          sources,
          followups,
        },
      ]);
    } catch (reason) {
      setChatError(
        reason instanceof ApiError && reason.status === 503
          ? "The assistant provider is unavailable. Your message was not answered."
          : "The assistant could not return a usable response.",
      );
    } finally {
      setSending(false);
    }
  }

  function startNewConversation() {
    setTurns([]);
    setDraft("");
    setChatError(null);
  }

  const supportedLanguages = stringList(status?.supported_languages);
  const statusLimitations = stringList(status?.limitations);

  return (
    <div className="assistant-page">
      <PageHeading
        eyebrow={t("assistant")}
        title={t("assistant")}
        intro="A conversational interface for evidence-backed agricultural questions. Replies appear only when the configured service returns a real answer and its available source citations."
      />
      <section className="assistant-product-layout">
        <section className="assistant-chat">
          <header className="assistant-chat-heading">
            <div>
              <p className="eyebrow">Grounded agricultural assistant</p>
              <h2>
                {turns.length
                  ? "Your conversation"
                  : "What would you like to understand?"}
              </h2>
            </div>
            <div
              className="assistant-header-actions"
              style={{ display: "flex", alignItems: "center", gap: 10 }}
            >
              {turns.length > 0 && (
                <button
                  className="icon-button"
                  onClick={startNewConversation}
                  type="button"
                >
                  + New chat
                </button>
              )}
              <span className={`status-label ${canChat ? "ready" : "pending"}`}>
                {canChat ? "Experimental" : "Unavailable"}
              </span>
            </div>
          </header>
          <ApiStatus loading={statusLoading} error={statusError} />
          {!turns.length && (
            <div className="assistant-welcome">
              <span className="assistant-welcome-mark" aria-hidden="true">
                <AiAssistantIcon size={40} />
              </span>
              <p>
                {canChat
                  ? "Ask a question; answers and citations will be returned by the connected assistant."
                  : "The assistant is not connected yet. You can still explore every available analysis and its supporting research."}
              </p>
              <div className="assistant-suggestions">
                {visibleSuggestions.map((question) => (
                  <button
                    disabled={!canChat}
                    key={question}
                    onClick={() => setDraft(question)}
                    type="button"
                  >
                    {question}
                    <span aria-hidden="true">↗</span>
                  </button>
                ))}
              </div>
            </div>
          )}
          {turns.length > 0 && (
            <div aria-live="polite" className="assistant-transcript">
              {turns.map((turn, index) => (
                <article
                  className={`chat-turn chat-${turn.role}`}
                  key={`${turn.role}-${index}`}
                >
                  <span className="chat-avatar">
                    {turn.role === "user" ? "You" : "BC"}
                  </span>
                  <div className="chat-bubble">
                    {turn.role === "assistant" ? (
                      <MarkdownMessage content={turn.content} />
                    ) : (
                      <p>{turn.content}</p>
                    )}
                    {turn.sources?.length ? (
                      <div className="chat-citations">
                        <strong>Sources</strong>
                        {turn.sources.map((source, sourceIndex) => (
                          <Citation key={sourceIndex} source={source} />
                        ))}
                      </div>
                    ) : null}
                    {turn.followups?.length ? (
                      <div className="chat-followups">
                        {turn.followups.map((question) => (
                          <button
                            key={question}
                            onClick={() => setDraft(question)}
                            type="button"
                          >
                            {question}
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </div>
                </article>
              ))}
              {sending && (
                <p className="loading-line" role="status">
                  Waiting for the assistant response…
                </p>
              )}
            </div>
          )}
          <form
            className="assistant-composer"
            onSubmit={(event) => void sendMessage(event)}
          >
            <label className="sr-only" htmlFor="assistant-question">
              {t("compose")}
            </label>
            <textarea
              id="assistant-question"
              maxLength={1000}
              onChange={(event) => setDraft(event.target.value)}
              placeholder={t("compose")}
              value={draft}
            />
            <button
              className="primary-button"
              disabled={!canChat || sending || !draft.trim()}
              type="submit"
            >
              {sending ? "Sending…" : t("send")}
            </button>
          </form>
          <ApiStatus loading={false} error={chatError} />
        </section>

        <aside className="assistant-evidence">
          <section className="resource-section">
            <p className="eyebrow">Service context</p>
            <h2>Assistant status</h2>
            <dl className="provenance-list">
              <div>
                <dt>Service</dt>
                <dd>{textFrom(status ?? {}, ["status"], "Not confirmed")}</dd>
              </div>
              <div>
                <dt>Provider</dt>
                <dd>
                  {formatProvider(
                    textFrom(status ?? {}, ["provider"], "Not configured"),
                  )}
                </dd>
              </div>
              <div>
                <dt>Language support</dt>
                <dd>
                  {supportedLanguages.length
                    ? supportedLanguages.join(", ")
                    : "English · Hindi interface"}
                </dd>
              </div>
            </dl>
            {statusLimitations.map((item) => (
              <p className="assistant-limitation" key={item}>
                {item}
              </p>
            ))}
            {capability?.availability === "available" ? (
              <p className="assistant-limitation">
                {t("assistantConfigReady")}
              </p>
            ) : (
              <div className="assistant-config-note">
                <p>{t("assistantConfigNote")}</p>
                <details className="assistant-config-details">
                  <summary>{t("assistantConfigTitle")}</summary>
                  <p>{t("assistantConfigIntro")}</p>
                  <p className="assistant-config-env-label">
                    {t("assistantConfigEnv")}:
                  </p>
                  <ul className="assistant-config-env">
                    <li>
                      <code>LLM_PROVIDER</code> = openai | openai_compatible |
                      generic
                    </li>
                    <li>
                      <code>LLM_API_KEY</code> = your provider API key
                    </li>
                    <li>
                      <code>LLM_MODEL</code> (optional; default gpt-4o-mini)
                    </li>
                    <li>
                      <code>LLM_BASE_URL</code> (optional; OpenAI-compatible
                      endpoint)
                    </li>
                  </ul>
                  <p className="assistant-config-hint">
                    {t("assistantConfigHint")}
                  </p>
                </details>
              </div>
            )}
          </section>
          <section className="resource-section">
            <p className="eyebrow">Location context</p>
            <h2>Optional context</h2>
            <div className="field">
              <label htmlFor="assistant-state">State</label>
              <input
                id="assistant-state"
                onChange={(event) =>
                  setLocation((current) => ({
                    ...current,
                    state: event.target.value,
                  }))
                }
                value={location.state}
              />
            </div>
            <div className="field">
              <label htmlFor="assistant-district">District</label>
              <input
                id="assistant-district"
                onChange={(event) =>
                  setLocation((current) => ({
                    ...current,
                    district: event.target.value,
                  }))
                }
                value={location.district}
              />
            </div>
            <p className="assistant-rail-note">
              Your location is sent only with a message and is not retained
              here.
            </p>
          </section>
          {lastAssistantTurn && (
            <section className="resource-section">
              <p className="eyebrow">Evidence from this answer</p>
              {lastAssistantTurn.sources?.length ? (
                lastAssistantTurn.sources.map((source, index) => (
                  <Citation key={index} source={source} />
                ))
              ) : (
                <p className="data-message">
                  No source citation was returned for the latest answer.
                </p>
              )}
            </section>
          )}
          {!canChat && (
            <section className="assistant-available-links">
              <strong>Continue exploring</strong>
              <Link href="/yield">
                Yield prediction <span>↗</span>
              </Link>
              <Link href="/research">
                Research & models <span>↗</span>
              </Link>
              <Link href="/model-development">
                Model selection lesson <span>↗</span>
              </Link>
            </section>
          )}
        </aside>
      </section>
    </div>
  );
}

function Citation({ source }: { source: ApiRecord }) {
  const title = textFrom(
    source,
    ["title", "name", "source", "citation"],
    "Source reference",
  );
  const url = source.url ?? source.href;
  if (typeof url === "string" && url.startsWith("https://")) {
    return (
      <a className="citation-link" href={url} rel="noreferrer" target="_blank">
        {title} <span aria-hidden="true">↗</span>
      </a>
    );
  }
  return <span className="citation-link">{title}</span>;
}

function normalizeSuggestions(response: ApiRecord): ApiRecord[] {
  const value = response.suggestions;
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (isApiRecord(item)) return [item];
    if (typeof item === "string" && item.trim()) return [{ en: item }];
    return [];
  });
}

function stringList(value: unknown) {
  return Array.isArray(value)
    ? value.filter(
        (item): item is string => typeof item === "string" && !!item.trim(),
      )
    : [];
}
