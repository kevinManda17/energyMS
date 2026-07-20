import { useEffect, useRef, useState } from "react";
import { Bot, Mic, Send, Square, User, Zap, AlertTriangle } from "lucide-react";
import { PageHeader } from "../components/ui";
import { neraApi } from "../api/endpoints";
import { useHouseId } from "../hooks/useHouseId";

/* N.E.R.A. — conversation avec l'assistante du micro-réseau.
 *
 * Deux entrées : le clavier (toujours disponible) et le micro. Le micro exige
 * un contexte sécurisé (HTTPS ou localhost) : sur une adresse LAN en clair
 * comme http://192.168.84.117:5173, le navigateur bloque getUserMedia. On le
 * détecte et on l'explique au lieu de laisser un bouton qui échoue en silence.
 * L'application mobile n'a pas cette contrainte : c'est là que la voix
 * fonctionne le mieux. */

const SUGGESTIONS = [
  "Quelles lampes sont allumées ?",
  "Éteins la lampe de 20 watts",
  "Quelle est la puissance actuelle ?",
  "Que recommande le système expert ?",
];

export default function Nera() {
  const houseId = useHouseId();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState(null);

  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const endRef = useRef(null);

  // Le micro exige HTTPS ou localhost — cf. commentaire en tête de fichier.
  const micAvailable =
    typeof window !== "undefined" &&
    window.isSecureContext &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof MediaRecorder !== "undefined";

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  function push(role, content, extra = {}) {
    setMessages((m) => [...m, { role, content, ...extra }]);
  }

  function handleResult(data, userText) {
    if (userText) push("user", userText);
    push("assistant", data.reply, { actions: data.actions });
    if (data.audio_base64) {
      // La réponse parlée renvoyée par le backend (TTS), jouée telle quelle.
      new Audio(`data:audio/mp3;base64,${data.audio_base64}`).play().catch(() => {});
    }
  }

  async function sendText(text) {
    const message = (text ?? input).trim();
    if (!message || !houseId || busy) return;
    setInput("");
    setError(null);
    push("user", message);
    setBusy(true);
    try {
      // On ne renvoie que les échanges, pas les actions : le modèle n'a pas
      // besoin de relire ses propres appels d'outils.
      const history = messages.map(({ role, content }) => ({ role, content }));
      const data = await neraApi.chat(houseId, message, history);
      handleResult(data, null);
    } catch (e) {
      setError(
        e?.response?.data?.detail ||
          "NERA est injoignable. Vérifiez que le backend tourne et que la clé OpenAI est configurée."
      );
    } finally {
      setBusy(false);
    }
  }

  async function startRecording() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => e.data.size && chunksRef.current.push(e.data);
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        if (blob.size < 1000) return; // clic accidentel : rien d'exploitable
        setBusy(true);
        try {
          const data = await neraApi.voice(houseId, blob, { speak: true });
          handleResult(data, data.transcript);
        } catch (e) {
          setError(
            e?.response?.data?.detail || "La transcription a échoué. Réessayez."
          );
        } finally {
          setBusy(false);
        }
      };
      recorder.start();
      recorderRef.current = recorder;
      setRecording(true);
    } catch {
      setError("Micro inaccessible. Autorisez-le dans le navigateur.");
    }
  }

  function stopRecording() {
    recorderRef.current?.stop();
    recorderRef.current = null;
    setRecording(false);
  }

  return (
    <>
      <PageHeader
        title="N.E.R.A."
        subtitle="Interrogez et commandez votre micro-réseau en langage naturel."
      />

      {!houseId && (
        <div className="card mb-4 p-5 text-sm text-slate-500">
          Sélectionnez d'abord un micro-réseau.
        </div>
      )}

      <div className="card flex h-[calc(100vh-16rem)] min-h-[26rem] flex-col p-0">
        {/* Fil de conversation */}
        <div className="flex-1 space-y-4 overflow-y-auto p-5">
          {messages.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center text-center">
              <span className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-electric/10">
                <Bot size={22} className="text-electric" strokeWidth={2.2} />
              </span>
              <p className="font-semibold text-navy dark:text-white">
                Bonjour, je suis NERA.
              </p>
              <p className="mb-4 max-w-sm text-sm text-slate-400">
                Je peux vous dire ce qui consomme et allumer ou éteindre vos lignes.
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => sendText(s)}
                    disabled={!houseId}
                    className="rounded-xl border border-slate-200 px-3 py-1.5 text-xs text-slate-500 transition hover:border-electric hover:text-electric disabled:opacity-40 dark:border-white/10"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <Message key={i} message={m} />
          ))}

          {busy && (
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <Bot size={15} className="text-electric" />
              <span className="animate-pulse">NERA réfléchit…</span>
            </div>
          )}
          <div ref={endRef} />
        </div>

        {error && (
          <div className="mx-5 mb-2 flex items-start gap-2 rounded-xl bg-red-50 px-3 py-2 text-xs text-danger dark:bg-red-500/10">
            <AlertTriangle size={14} className="mt-0.5 flex-shrink-0" />
            {error}
          </div>
        )}

        {/* Barre de saisie */}
        <div className="border-t border-slate-100 p-4 dark:border-white/5">
          <div className="flex items-center gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendText()}
              placeholder="Écrivez votre demande…"
              disabled={!houseId || busy}
              className="flex-1 rounded-xl border border-slate-200 bg-transparent px-4 py-2.5 text-sm outline-none transition focus:border-electric disabled:opacity-50 dark:border-white/10"
            />

            <button
              onClick={recording ? stopRecording : startRecording}
              disabled={!houseId || busy || !micAvailable}
              title={
                micAvailable
                  ? recording
                    ? "Arrêter l'enregistrement"
                    : "Parler"
                  : "Le micro exige HTTPS ou localhost — utilisez l'application mobile"
              }
              className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl transition disabled:cursor-not-allowed disabled:opacity-40 ${
                recording
                  ? "bg-danger text-white"
                  : "border border-slate-200 text-slate-500 hover:border-electric hover:text-electric dark:border-white/10"
              }`}
            >
              {recording ? <Square size={16} /> : <Mic size={17} />}
            </button>

            <button
              onClick={() => sendText()}
              disabled={!houseId || busy || !input.trim()}
              className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-electric text-white transition hover:opacity-90 disabled:opacity-40"
            >
              <Send size={16} />
            </button>
          </div>

          {!micAvailable && (
            <p className="mt-2 text-[11px] text-slate-400">
              Micro indisponible : les navigateurs l'exigent en HTTPS (ou sur
              localhost). Sur une adresse LAN en clair, utilisez le clavier — ou
              l'application mobile, qui n'a pas cette limite.
            </p>
          )}
        </div>
      </div>
    </>
  );
}

function Message({ message }) {
  const isUser = message.role === "user";
  // On n'affiche que les actions ayant réellement modifié une ligne : c'est ce
  // qui compte pour l'utilisateur, et ça ne se déduit pas du texte du modèle.
  const applied = (message.actions || []).filter(
    (a) => a.tool === "set_line" || a.tool === "set_all_lines"
  );

  return (
    <div className={`flex gap-2.5 ${isUser ? "flex-row-reverse" : ""}`}>
      <span
        className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl ${
          isUser ? "bg-slate-100 dark:bg-white/5" : "bg-electric/10"
        }`}
      >
        {isUser ? (
          <User size={15} className="text-slate-500" />
        ) : (
          <Bot size={15} className="text-electric" />
        )}
      </span>

      <div className={`max-w-[80%] ${isUser ? "text-right" : ""}`}>
        <div
          className={`inline-block rounded-2xl px-3.5 py-2 text-sm ${
            isUser
              ? "bg-electric text-white"
              : "bg-slate-50 text-navy dark:bg-white/5 dark:text-white"
          }`}
        >
          {message.content}
        </div>

        {applied.map((a, i) => (
          <div
            key={i}
            className="mt-1.5 inline-flex items-center gap-1.5 rounded-lg bg-green-50 px-2 py-1 text-[11px] font-semibold text-energy dark:bg-green-500/10"
          >
            <Zap size={11} />
            {describeAction(a)}
          </div>
        ))}
      </div>
    </div>
  );
}

function describeAction({ tool, arguments: args, result }) {
  if (result?.refus) return "Action refusée";
  if (tool === "set_line") {
    return `Ligne ${args.line} ${args.on ? "allumée" : "éteinte"}`;
  }
  const preserved = result?.lignes_preservees;
  return `Toutes les lignes ${args.on ? "allumées" : "éteintes"}${
    preserved?.length ? ` (ligne ${preserved.join(", ")} préservée)` : ""
  }`;
}
