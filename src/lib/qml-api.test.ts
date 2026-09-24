import { describe, expect, test } from "bun:test";

import { parseQmlCsv } from "./qml-api";

describe("parseQmlCsv", () => {
  test("maps an exact one-row schema even when columns are reordered", () => {
    expect(parseQmlCsv("AGE,SEX\n48,2", ["SEX", "AGE"])).toEqual({ AGE: 48, SEX: 2 });
  });

  test("keeps an explicit empty value for model-side imputation", () => {
    expect(parseQmlCsv("SEX,AGE\n2,", ["SEX", "AGE"])).toEqual({ SEX: 2, AGE: null });
  });

  test("rejects missing, extra, duplicate and additional data rows", () => {
    expect(() => parseQmlCsv("SEX\n2", ["SEX", "AGE"])).toThrow("exactly these headers");
    expect(() => parseQmlCsv("SEX,AGE,OUTCOME\n2,48,1", ["SEX", "AGE"])).toThrow(
      "exactly these headers",
    );
    expect(() => parseQmlCsv("SEX,SEX\n2,2", ["SEX", "AGE"])).toThrow("exactly these headers");
    expect(() => parseQmlCsv("SEX,AGE\n2,48\n1,51", ["SEX", "AGE"])).toThrow(
      "exactly one data row",
    );
  });

  test("rejects non-numeric input and malformed quotes", () => {
    expect(() => parseQmlCsv("SEX,AGE\n2,unknown", ["SEX", "AGE"])).toThrow("AGE must be numeric");
    expect(() => parseQmlCsv('SEX,AGE\n2,"48', ["SEX", "AGE"])).toThrow("unclosed");
  });
});
