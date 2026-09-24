import { createContext, useContext, useState, type ReactNode } from "react";
import type { QmlPrediction, QmlRequest } from "./qml-api";

type QmlCurrent = { request: QmlRequest; prediction: QmlPrediction } | null;
const QmlContext = createContext<{
  current: QmlCurrent;
  setCurrent: (value: QmlCurrent) => void;
} | null>(null);

export function QmlSessionProvider({ children }: { children: ReactNode }) {
  const [current, setCurrent] = useState<QmlCurrent>(null);
  return <QmlContext.Provider value={{ current, setCurrent }}>{children}</QmlContext.Provider>;
}

export function useQmlSession() {
  const value = useContext(QmlContext);
  if (!value) throw new Error("QML session provider is missing");
  return value;
}
