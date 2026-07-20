import { useEffect, useRef, useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ScrollView, KeyboardAvoidingView, Platform, ActivityIndicator,
} from "react-native";
import { Audio } from "expo-av";
import { Bot, Mic, Send, Square, User, Zap } from "lucide-react-native";
import { Screen, PageTitle } from "../components/Screen";
import { neraApi } from "../api/endpoints";
import { useActiveHouse } from "../hooks/useActiveHouse";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";

/* N.E.R.A. sur mobile — c'est ici que la voix prend tout son sens : contrairement
 * au navigateur, l'application n'exige pas de HTTPS pour accéder au micro.
 *
 * Cycle : maintenir le micro -> enregistrer -> relâcher -> le backend transcrit,
 * agit, répond, et renvoie la réponse parlée que l'on joue directement. */

const SUGGESTIONS = [
  "Quelles lampes sont allumées ?",
  "Éteins la lampe de 20 watts",
  "Quelle est la puissance actuelle ?",
];

export default function NeraScreen() {
  const t = useTheme();
  const { activeHouse } = useActiveHouse();
  const houseId = activeHouse?.id;

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(null);
  const [error, setError] = useState(null);

  const scrollRef = useRef(null);
  const soundRef = useRef(null);

  // Libère le lecteur audio en quittant l'écran : sans cela, une réponse
  // continuerait de jouer après la navigation.
  useEffect(() => () => { soundRef.current?.unloadAsync?.(); }, []);

  function push(role, content, extra = {}) {
    setMessages((m) => [...m, { role, content, ...extra }]);
    setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 80);
  }

  async function playReply(base64) {
    if (!base64) return;
    try {
      await soundRef.current?.unloadAsync?.();
      const { sound } = await Audio.Sound.createAsync(
        { uri: `data:audio/mp3;base64,${base64}` },
        { shouldPlay: true }
      );
      soundRef.current = sound;
    } catch {
      // La réponse écrite reste affichée : l'échec audio n'est pas bloquant.
    }
  }

  function handleResult(data, userText) {
    if (userText) push("user", userText);
    push("assistant", data.reply, { actions: data.actions });
    playReply(data.audio_base64);
  }

  async function sendText(text) {
    const message = (text ?? input).trim();
    if (!message || !houseId || busy) return;
    setInput("");
    setError(null);
    push("user", message);
    setBusy(true);
    try {
      const history = messages.map(({ role, content }) => ({ role, content }));
      const data = await neraApi.chat(houseId, message, history);
      handleResult(data, null);
    } catch (e) {
      setError(e?.response?.data?.detail || "NERA est injoignable.");
    } finally {
      setBusy(false);
    }
  }

  async function startRecording() {
    setError(null);
    try {
      const perm = await Audio.requestPermissionsAsync();
      if (!perm.granted) {
        setError("Autorisez l'accès au micro pour parler à NERA.");
        return;
      }
      // Nécessaire sur iOS : sans ce mode, l'enregistrement reste silencieux.
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });
      const { recording: rec } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      setRecording(rec);
    } catch {
      setError("Impossible de démarrer l'enregistrement.");
    }
  }

  async function stopRecording() {
    const rec = recording;
    if (!rec) return;
    setRecording(null);
    setBusy(true);
    try {
      await rec.stopAndUnloadAsync();
      // On repasse en lecture, sinon la réponse vocale sortirait dans l'écouteur.
      await Audio.setAudioModeAsync({ allowsRecordingIOS: false });
      const uri = rec.getURI();
      const data = await neraApi.voice(houseId, uri, { speak: true });
      if (!data.transcript) {
        setError("Je n'ai rien entendu. Réessayez.");
      } else {
        handleResult(data, data.transcript);
      }
    } catch (e) {
      setError(e?.response?.data?.detail || "La transcription a échoué.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen>
      <PageTitle title="N.E.R.A." subtitle={activeHouse?.name || "Aucun micro-réseau"} />

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={90}
      >
        <ScrollView ref={scrollRef} style={{ flex: 1 }} contentContainerStyle={{ paddingBottom: 12 }}>
          {messages.length === 0 && (
            <View style={styles.empty}>
              <View style={[styles.avatar, { backgroundColor: palette.blueLight }]}>
                <Bot color={palette.blue} size={22} strokeWidth={2.2} />
              </View>
              <Text style={[styles.emptyTitle, { color: t.text }]}>Bonjour, je suis NERA.</Text>
              <Text style={[styles.emptyText, { color: t.sub }]}>
                Maintenez le micro pour me parler, ou écrivez votre demande.
              </Text>
              {SUGGESTIONS.map((s) => (
                <TouchableOpacity
                  key={s}
                  style={[styles.suggestion, { borderColor: t.border }]}
                  onPress={() => sendText(s)}
                  disabled={!houseId}
                  activeOpacity={0.8}
                >
                  <Text style={{ color: t.sub, fontSize: 12 }}>{s}</Text>
                </TouchableOpacity>
              ))}
            </View>
          )}

          {messages.map((m, i) => (
            <Bubble key={i} message={m} t={t} />
          ))}

          {busy && (
            <View style={styles.thinking}>
              <ActivityIndicator size="small" color={palette.blue} />
              <Text style={{ color: t.sub, fontSize: 12 }}>NERA réfléchit…</Text>
            </View>
          )}
        </ScrollView>

        {error && (
          <Text style={styles.error}>{error}</Text>
        )}

        <View style={[styles.bar, { borderTopColor: t.border }]}>
          <TextInput
            style={[styles.input, { color: t.text, borderColor: t.border }]}
            value={input}
            onChangeText={setInput}
            onSubmitEditing={() => sendText()}
            placeholder="Écrivez votre demande…"
            placeholderTextColor={t.sub}
            editable={!!houseId && !busy}
            returnKeyType="send"
          />

          <TouchableOpacity
            style={[
              styles.iconBtn,
              recording
                ? { backgroundColor: palette.danger }
                : { borderWidth: 1, borderColor: t.border },
              (!houseId || busy) && { opacity: 0.4 },
            ]}
            onPressIn={startRecording}
            onPressOut={stopRecording}
            disabled={!houseId || busy}
            activeOpacity={0.8}
          >
            {recording
              ? <Square color="#fff" size={16} />
              : <Mic color={t.sub} size={18} />}
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.iconBtn,
              { backgroundColor: palette.blue },
              (!houseId || busy || !input.trim()) && { opacity: 0.4 },
            ]}
            onPress={() => sendText()}
            disabled={!houseId || busy || !input.trim()}
            activeOpacity={0.8}
          >
            <Send color="#fff" size={16} />
          </TouchableOpacity>
        </View>

        <Text style={[styles.hint, { color: t.sub }]}>
          {recording ? "Enregistrement… relâchez pour envoyer." : "Maintenez le micro pour parler."}
        </Text>
      </KeyboardAvoidingView>
    </Screen>
  );
}

function Bubble({ message, t }) {
  const isUser = message.role === "user";
  // Seules les actions ayant modifié une ligne intéressent l'utilisateur.
  const applied = (message.actions || []).filter(
    (a) => a.tool === "set_line" || a.tool === "set_all_lines"
  );

  return (
    <View style={[styles.row, isUser && { flexDirection: "row-reverse" }]}>
      <View style={[styles.bubbleAvatar, { backgroundColor: isUser ? "#F1F5F9" : palette.blueLight }]}>
        {isUser
          ? <User color={palette.slate} size={14} />
          : <Bot color={palette.blue} size={14} />}
      </View>
      <View style={{ flex: 1, alignItems: isUser ? "flex-end" : "flex-start" }}>
        <View
          style={[
            styles.bubble,
            isUser
              ? { backgroundColor: palette.blue }
              : { backgroundColor: t.card, borderWidth: 1, borderColor: t.border },
          ]}
        >
          <Text style={{ color: isUser ? "#fff" : t.text, fontSize: 14, lineHeight: 19 }}>
            {message.content}
          </Text>
        </View>

        {applied.map((a, i) => (
          <View key={i} style={styles.actionChip}>
            <Zap color={palette.green} size={11} />
            <Text style={{ color: palette.green, fontSize: 11, fontWeight: "700" }}>
              {describeAction(a)}
            </Text>
          </View>
        ))}
      </View>
    </View>
  );
}

function describeAction({ tool, arguments: args, result }) {
  if (result?.refus) return "Action refusée";
  if (tool === "set_line") return `Ligne ${args.line} ${args.on ? "allumée" : "éteinte"}`;
  const preserved = result?.lignes_preservees;
  return `Toutes les lignes ${args.on ? "allumées" : "éteintes"}${
    preserved?.length ? ` (ligne ${preserved.join(", ")} préservée)` : ""
  }`;
}

const styles = StyleSheet.create({
  empty: { alignItems: "center", paddingVertical: 32, gap: 8 },
  avatar: { width: 48, height: 48, borderRadius: 16, alignItems: "center", justifyContent: "center", marginBottom: 6 },
  emptyTitle: { fontSize: 15, fontWeight: "800" },
  emptyText: { fontSize: 13, textAlign: "center", marginBottom: 8, paddingHorizontal: 24 },
  suggestion: { borderWidth: 1, borderRadius: 12, paddingVertical: 8, paddingHorizontal: 14 },
  row: { flexDirection: "row", gap: 8, marginBottom: 12, alignItems: "flex-start" },
  bubbleAvatar: { width: 30, height: 30, borderRadius: 10, alignItems: "center", justifyContent: "center" },
  bubble: { borderRadius: 16, paddingHorizontal: 13, paddingVertical: 9, maxWidth: "88%" },
  actionChip: {
    flexDirection: "row", alignItems: "center", gap: 5, marginTop: 5,
    backgroundColor: "#DCFCE7", borderRadius: 8, paddingHorizontal: 8, paddingVertical: 4,
  },
  thinking: { flexDirection: "row", alignItems: "center", gap: 8, paddingVertical: 8 },
  error: { color: palette.danger, fontSize: 12, marginBottom: 6 },
  bar: { flexDirection: "row", alignItems: "center", gap: 8, borderTopWidth: 1, paddingTop: 10 },
  input: { flex: 1, borderWidth: 1, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 10, fontSize: 14 },
  iconBtn: { width: 42, height: 42, borderRadius: 12, alignItems: "center", justifyContent: "center" },
  hint: { fontSize: 11, textAlign: "center", marginTop: 6 },
});
