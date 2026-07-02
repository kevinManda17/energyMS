import { NavigationContainer, DefaultTheme, DarkTheme } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { useColorScheme, View, Text, StyleSheet } from "react-native";
import {
  BarChart2,
  Home,
  MoreHorizontal,
  Network,
  Zap,
} from "lucide-react-native";

import { useAuthStore } from "../store/auth";
import { palette } from "../theme/colors";

import LoginScreen from "../screens/LoginScreen";
import RegisterScreen from "../screens/RegisterScreen";
import DashboardScreen from "../screens/DashboardScreen";
import HousesScreen from "../screens/HousesScreen";
import HistoryScreen from "../screens/HistoryScreen";
import DecisionsScreen from "../screens/DecisionsScreen";
import AlertsScreen from "../screens/AlertsScreen";
import SettingsScreen from "../screens/SettingsScreen";
import DecisionDetailScreen from "../screens/DecisionDetailScreen";
import AlertDetailScreen from "../screens/AlertDetailScreen";
import DevicesScreen from "../screens/DevicesScreen";
import ForecastingScreen from "../screens/ForecastingScreen";
import ReportsScreen from "../screens/ReportsScreen";
import PricingScreen from "../screens/PricingScreen";
import MoreScreen from "../screens/MoreScreen";
import ProfileScreen from "../screens/ProfileScreen";
import PasswordScreen from "../screens/PasswordScreen";
import DisplayScreen from "../screens/DisplayScreen";
import NotificationsScreen from "../screens/NotificationsScreen";
import NetworkScreen from "../screens/NetworkScreen";
import PrivacyScreen from "../screens/PrivacyScreen";

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

const TAB_ICONS = {
  Accueil: Home,
  Reseaux: Network,
  Mesures: BarChart2,
  Decisions: Zap,
  Plus: MoreHorizontal,
};

const TAB_LABELS = {
  Accueil: "Accueil",
  Reseaux: "Réseaux",
  Mesures: "Mesures",
  Decisions: "Décisions",
  Plus: "Plus",
};

function Tabs() {
  const scheme = useColorScheme();
  const isDark = scheme === "dark";

  return (
    <Tab.Navigator
      screenOptions={({ route }) => {
        const Icon = TAB_ICONS[route.name] || MoreHorizontal;
        return {
          headerShown: false,
          tabBarActiveTintColor: palette.blue,
          tabBarInactiveTintColor: isDark ? "#475569" : "#94A3B8",
          tabBarLabelStyle: {
            fontWeight: "700",
            fontSize: 10.5,
            marginBottom: 2,
          },
          tabBarStyle: {
            backgroundColor: isDark ? "#0F1929" : "#FFFFFF",
            borderTopWidth: 1,
            borderTopColor: isDark ? "rgba(255,255,255,0.06)" : "#E2E8F0",
            height: 64,
            paddingBottom: 8,
            paddingTop: 6,
            elevation: 12,
            shadowColor: "#000",
            shadowOffset: { width: 0, height: -2 },
            shadowOpacity: 0.06,
            shadowRadius: 8,
          },
          tabBarLabel: TAB_LABELS[route.name] || route.name,
          tabBarIcon: ({ color, focused }) => (
            <View style={focused ? styles.iconActive : styles.icon}>
              <Icon
                color={color}
                size={22}
                strokeWidth={focused ? 2.6 : 2}
              />
            </View>
          ),
        };
      }}
    >
      <Tab.Screen name="Accueil" component={DashboardScreen} />
      <Tab.Screen name="Reseaux" component={HousesScreen} />
      <Tab.Screen name="Mesures" component={HistoryScreen} />
      <Tab.Screen name="Decisions" component={DecisionsScreen} />
      <Tab.Screen name="Plus" component={MoreScreen} />
    </Tab.Navigator>
  );
}

const stackScreenOptions = {
  headerStyle: { backgroundColor: palette.blue },
  headerTintColor: "#fff",
  headerTitleStyle: { fontWeight: "800", fontSize: 17 },
  headerShadowVisible: false,
};

export default function Navigation() {
  const scheme = useColorScheme();
  const { isAuthenticated } = useAuthStore();

  return (
    <NavigationContainer theme={scheme === "dark" ? DarkTheme : DefaultTheme}>
      <Stack.Navigator>
        {isAuthenticated ? (
          <>
            <Stack.Screen name="Main" component={Tabs} options={{ headerShown: false }} />
            <Stack.Screen name="DecisionDetail" component={DecisionDetailScreen} options={{ ...stackScreenOptions, title: "Détail décision" }} />
            <Stack.Screen name="AlertDetail" component={AlertDetailScreen} options={{ ...stackScreenOptions, title: "Détail alerte" }} />
            <Stack.Screen name="Devices" component={DevicesScreen} options={{ ...stackScreenOptions, title: "Équipements" }} />
            <Stack.Screen name="Forecasting" component={ForecastingScreen} options={{ ...stackScreenOptions, title: "Prévisions horaires" }} />
            <Stack.Screen name="Reports" component={ReportsScreen} options={{ ...stackScreenOptions, title: "Rapports" }} />
            <Stack.Screen name="Pricing" component={PricingScreen} options={{ ...stackScreenOptions, title: "Tarifs" }} />
            <Stack.Screen name="Settings"       component={SettingsScreen}       options={{ ...stackScreenOptions, title: "Paramètres"      }} />
            <Stack.Screen name="Profile"        component={ProfileScreen}        options={{ ...stackScreenOptions, title: "Mon profil"       }} />
            <Stack.Screen name="Password"       component={PasswordScreen}       options={{ ...stackScreenOptions, title: "Mot de passe"     }} />
            <Stack.Screen name="Display"        component={DisplayScreen}        options={{ ...stackScreenOptions, title: "Affichage"        }} />
            <Stack.Screen name="Notifications"  component={NotificationsScreen}  options={{ ...stackScreenOptions, title: "Notifications"    }} />
            <Stack.Screen name="Network"        component={NetworkScreen}        options={{ ...stackScreenOptions, title: "Réseau"           }} />
            <Stack.Screen name="Privacy"        component={PrivacyScreen}        options={{ ...stackScreenOptions, title: "Confidentialité"  }} />
          </>
        ) : (
          <>
            <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
            <Stack.Screen name="Register" component={RegisterScreen} options={{ headerShown: false }} />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  icon: {
    width: 28,
    height: 28,
    alignItems: "center",
    justifyContent: "center",
  },
  iconActive: {
    width: 28,
    height: 28,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 8,
    backgroundColor: palette.blue + "14",
  },
});
