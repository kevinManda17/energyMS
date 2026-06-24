import { useState } from "react";
import { StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { Eye, EyeOff } from "lucide-react-native";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";

export function FormInput({
  label,
  icon: Icon,
  secureTextEntry,
  containerStyle,
  inputStyle,
  textContentType,
  ...props
}) {
  const t = useTheme();
  const [hidden, setHidden] = useState(!!secureTextEntry);
  const isPassword = !!secureTextEntry;

  return (
    <View style={[styles.wrap, containerStyle]}>
      {label ? <Text style={[styles.label, { color: t.text }]}>{label}</Text> : null}
      <View style={[styles.box, { borderColor: t.border, backgroundColor: t.card }]}>
        {Icon ? <Icon size={19} color={t.sub} strokeWidth={2.2} /> : null}
        <TextInput
          key={isPassword ? (hidden ? "password-hidden" : "password-visible") : "plain"}
          style={[
            styles.input,
            { color: t.text, backgroundColor: "transparent" },
            inputStyle,
          ]}
          placeholderTextColor={t.sub}
          secureTextEntry={isPassword ? hidden : false}
          textContentType={textContentType || (isPassword ? "password" : "none")}
          underlineColorAndroid="transparent"
          selectionColor={palette.blue}
          autoCapitalize="none"
          {...props}
        />
        {secureTextEntry ? (
          <TouchableOpacity
            accessibilityLabel={hidden ? "Afficher le mot de passe" : "Masquer le mot de passe"}
            onPress={() => setHidden((current) => !current)}
            style={styles.eyeButton}
          >
            {hidden ? (
              <Eye size={20} color={palette.blue} strokeWidth={2.2} />
            ) : (
              <EyeOff size={20} color={palette.blue} strokeWidth={2.2} />
            )}
          </TouchableOpacity>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginTop: 12 },
  label: { fontSize: 13, fontWeight: "700", marginBottom: 6 },
  box: {
    minHeight: 50,
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 12,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  input: { flex: 1, fontSize: 15, paddingVertical: 10 },
  eyeButton: { width: 34, height: 34, alignItems: "center", justifyContent: "center" },
});
