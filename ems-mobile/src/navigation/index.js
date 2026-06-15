import { NavigationContainer, DefaultTheme, DarkTheme } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { useColorScheme, Text } from "react-native";

import { useAuthStore } from "../store/auth";
import { palette } from "../theme/colors";

import LoginScreen from "../screens/LoginScreen";
import RegisterScreen from "../screens/RegisterScreen";
import DashboardScreen from "../screens/DashboardScreen";
import HistoryScreen from "../screens/HistoryScreen";
import AlertsScreen from "../screens/AlertsScreen";
import SettingsScreen from "../screens/SettingsScreen";
import DecisionDetailScreen from "../screens/DecisionDetailScreen";
import AlertDetailScreen from "../screens/AlertDetailScreen";

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

const ICONS = { Accueil: "⌂", Historique: "≣", Alertes: "!", Paramètres: "⚙" };

function Tabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: palette.blue,
        tabBarIcon: ({ color }) => (
          <Text style={{ color, fontSize: 18 }}>{ICONS[route.name]}</Text>
        ),
      })}
    >
      <Tab.Screen name="Accueil" component={DashboardScreen} />
      <Tab.Screen name="Historique" component={HistoryScreen} />
      <Tab.Screen name="Alertes" component={AlertsScreen} />
      <Tab.Screen name="Paramètres" component={SettingsScreen} />
    </Tab.Navigator>
  );
}

export default function Navigation() {
  const scheme = useColorScheme();
  const { isAuthenticated } = useAuthStore();

  return (
    <NavigationContainer theme={scheme === "dark" ? DarkTheme : DefaultTheme}>
      <Stack.Navigator>
        {isAuthenticated ? (
          <>
            <Stack.Screen name="Main" component={Tabs} options={{ headerShown: false }} />
            <Stack.Screen name="DecisionDetail" component={DecisionDetailScreen} options={{ title: "Décision" }} />
            <Stack.Screen name="AlertDetail" component={AlertDetailScreen} options={{ title: "Alerte" }} />
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
