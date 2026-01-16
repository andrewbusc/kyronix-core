import { useEffect, useMemo, useState } from "react";

import {
  deletePaystub,
  downloadPaystubPdf,
  generatePaystubPdf,
  listPaystubsForUser,
  listUsers,
  uploadPaystub,
} from "../../api/client";
import type { User } from "../../App";

type PayType = "SALARY" | "HOURLY" | "CONTRACTOR";

type PaystubSummary = {
  id: number;
  pay_date: string;
  pay_period_start: string;
  pay_period_end: string;
  file_name: string;
};

type PaystubListResponse = {
  items: PaystubSummary[];
  available_years: number[];
};

type EarningsLine = {
  description: string;
  hours: number | null;
  rate: number | null;
  current_amount: number;
  ytd_amount: number;
};

type DeductionLine = {
  deduction_name: string;
  current_amount: number;
  ytd_amount: number;
};

type TotalsLine = {
  gross_pay_current: number;
  total_deductions_current: number;
  net_pay_current: number;
  gross_pay_ytd: number;
  total_deductions_ytd: number;
  net_pay_ytd: number;
};

type PaystubDraft = {
  pay_date: string;
  pay_period_start: string;
  pay_period_end: string;
  earnings: EarningsLine[];
  deductions: DeductionLine[];
  totals: TotalsLine;
  leave_balances?: {
    vacation_accrued: number;
    vacation_used: number;
    vacation_balance: number;
    sick_accrued: number;
    sick_used: number;
    sick_balance: number;
  };
};

const FEDERAL_BRACKETS = [
  { min: 0, max: 48475, rate: 12 },
  { min: 48476, max: 103350, rate: 22 },
  { min: 103351, max: 197300, rate: 24 },
  { min: 197301, max: 250525, rate: 32 },
  { min: 250526, max: Number.POSITIVE_INFINITY, rate: 32 },
];

const PIT_CA_2026_SINGLE = [
  { min: 0, max: 11079, base: 0, rate: 1 },
  { min: 11079, max: 26264, base: 110.79, rate: 2 },
  { min: 26264, max: 41452, base: 414.49, rate: 4 },
  { min: 41452, max: 57542, base: 1022.01, rate: 6 },
  { min: 57542, max: 72724, base: 1987.41, rate: 8 },
  { min: 72724, max: 371479, base: 3201.97, rate: 9.3 },
  { min: 371479, max: 445771, base: 30986.19, rate: 10.3 },
  { min: 445771, max: 742953, base: 38651.56, rate: 11.3 },
  { min: 742953, max: Number.POSITIVE_INFINITY, base: 72217.2, rate: 12.3 },
];

const STANDARD_SDI_RATE = 1.1;
const VACATION_ACCRUAL_PER_PERIOD = 80 / 26;
const VACATION_CAP = 120;
const SICK_ACCRUAL_PER_PERIOD = 40 / 26;
const SICK_CAP = 80;

const roundCurrency = (value: number) => Math.round((value + Number.EPSILON) * 100) / 100;

const parseNumber = (value: string) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
};

const parseDate = (value: string) => {
  if (!value) {
    return null;
  }
  const parts = value.split("-").map(Number);
  if (parts.length !== 3) {
    return null;
  }
  const [year, month, day] = parts;
  return new Date(year, month - 1, day);
};

const formatDate = (date: Date) => {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const formatCompactDate = (date: Date) => {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${year}${month}${day}`;
};

const addDays = (date: Date, days: number) => {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
};

const formatCurrency = (value: number) => `$${value.toFixed(2)}`;

const getFederalRate = (annualPay: number) => {
  const bracket = FEDERAL_BRACKETS.find((entry) => annualPay >= entry.min && annualPay <= entry.max);
  return bracket ? bracket.rate : 0;
};

const calculatePitTax = (annualPay: number) => {
  if (annualPay <= 0) {
    return 0;
  }
  const bracket = PIT_CA_2026_SINGLE.find(
    (entry) => annualPay >= entry.min && annualPay <= entry.max
  );
  if (!bracket) {
    return 0;
  }
  const taxable = annualPay - bracket.min;
  return roundCurrency(bracket.base + taxable * (bracket.rate / 100));
};

const getPitEffectiveRate = (annualPay: number) => {
  if (annualPay <= 0) {
    return 0;
  }
  const annualTax = calculatePitTax(annualPay);
  return roundCurrency((annualTax / annualPay) * 100);
};

const isLastPayDateOfYear = (payDate: Date) => {
  const nextPayDate = addDays(payDate, 14);
  return nextPayDate.getFullYear() !== payDate.getFullYear();
};

const buildFileName = (employeeName: string, payDate: Date) => {
  const parts = employeeName.trim().split(/\s+/);
  const lastName = parts.length ? parts[parts.length - 1] : "EMPLOYEE";
  const sanitized = lastName.replace(/[^A-Za-z0-9]/g, "").toUpperCase() || "EMPLOYEE";
  return `KYRONIX_PAYSTUB_${sanitized}_${formatCompactDate(payDate)}.pdf`;
};

const formatEmployeeNumber = (value: number | string) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return `${value}`;
  }
  const base = numeric + 800;
  return `KC-${String(base).padStart(4, "0")}`;
};

export default function AdminPaystubs() {
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyYear, setHistoryYear] = useState("all");
  const [historyYears, setHistoryYears] = useState<number[]>([]);
  const [paystubHistory, setPaystubHistory] = useState<PaystubSummary[]>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadPayDate, setUploadPayDate] = useState("");
  const [uploadPeriodStart, setUploadPeriodStart] = useState("");
  const [uploadPeriodEnd, setUploadPeriodEnd] = useState("");
  const [uploadFileName, setUploadFileName] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  const [selectedUserId, setSelectedUserId] = useState("");
  const [employeeId, setEmployeeId] = useState("");
  const [employeeName, setEmployeeName] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [department, setDepartment] = useState("");
  const [employmentType, setEmploymentType] = useState<"Full-Time" | "Part-Time">("Full-Time");

  const [payType, setPayType] = useState<PayType>("SALARY");
  const [annualSalary, setAnnualSalary] = useState("");
  const [hourlyRate, setHourlyRate] = useState("");
  const [hoursWorked, setHoursWorked] = useState("80");

  const [hireDate, setHireDate] = useState("");
  const [mostRecentPayDate, setMostRecentPayDate] = useState("");
  const [paystubCount, setPaystubCount] = useState("1");

  const [companyAddress, setCompanyAddress] = useState(
    "28 Geary St Suite 650 San Francisco, CA 94108"
  );
  const [payrollEmail, setPayrollEmail] = useState("hr@kyronix.ai");
  const [companyLogoUrl, setCompanyLogoUrl] = useState(() => {
    if (typeof window === "undefined") {
      return "";
    }
    return `${window.location.origin}/brand/kyronix_logo_dark_on_light.png`;
  });

  const [paymentMethod, setPaymentMethod] = useState<"Direct Deposit" | "Check">("Direct Deposit");
  const [bankMasked, setBankMasked] = useState("Not provided");
  const [paymentStatus, setPaymentStatus] = useState("Processed");

  const [includeFederal, setIncludeFederal] = useState(true);
  const [includeSocialSecurity, setIncludeSocialSecurity] = useState(true);
  const [includeMedicare, setIncludeMedicare] = useState(true);
  const [includePit, setIncludePit] = useState(true);
  const [includeSdi, setIncludeSdi] = useState(true);
  const [includeHealth, setIncludeHealth] = useState(true);
  const [includeContractorFee, setIncludeContractorFee] = useState(false);
  const [include401k, setInclude401k] = useState(true);

  const [ssRate, setSsRate] = useState("6.2");
  const [medicareRate, setMedicareRate] = useState("1.45");
  const [pitRate, setPitRate] = useState("0");
  const [sdiRate, setSdiRate] = useState("0");
  const [healthAmount, setHealthAmount] = useState("119");
  const [contractorFeeRate, setContractorFeeRate] = useState("0");
  const [yearEndBonusRate, setYearEndBonusRate] = useState("0");
  const [rate401k, setRate401k] = useState("5");

  useEffect(() => {
    listUsers()
      .then((data) => setUsers(data))
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Unable to load employees");
      });
  }, []);

  useEffect(() => {
    const selected = users.find((entry) => `${entry.id}` === selectedUserId);
    if (!selected) {
      return;
    }
    setEmployeeId(formatEmployeeNumber(selected.id));
    setEmployeeName(`${selected.legal_first_name} ${selected.legal_last_name}`);
    setJobTitle(selected.job_title);
    setDepartment(selected.department);
    setHireDate(selected.hire_date);
  }, [selectedUserId, users]);

  useEffect(() => {
    setHistoryYear("all");
  }, [selectedUserId]);

  useEffect(() => {
    if (payType === "CONTRACTOR") {
      setIncludeFederal(false);
      setIncludeSocialSecurity(false);
      setIncludeMedicare(false);
      setIncludePit(false);
      setIncludeSdi(false);
      setIncludeHealth(false);
      setInclude401k(false);
    } else {
      setIncludeFederal(true);
      setIncludeSocialSecurity(true);
      setIncludeMedicare(true);
      setIncludePit(true);
      setIncludeSdi(true);
      setIncludeHealth(payType === "SALARY");
      setInclude401k(payType === "SALARY");
    }
  }, [payType]);

  const historyYearValue = useMemo(() => {
    if (historyYear === "all") {
      return undefined;
    }
    const parsed = Number(historyYear);
    return Number.isNaN(parsed) ? undefined : parsed;
  }, [historyYear]);

  useEffect(() => {
    if (payType === "CONTRACTOR") {
      setPitRate("0");
      setSdiRate("0");
      return;
    }

    const basePay =
      payType === "SALARY"
        ? parseNumber(annualSalary)
        : roundCurrency(parseNumber(hourlyRate) * 2080);
    const annualHealth = includeHealth ? roundCurrency(parseNumber(healthAmount) * 26) : 0;
    const annual401k =
      include401k && payType === "SALARY"
        ? roundCurrency((basePay * parseNumber(rate401k)) / 100)
        : 0;
    const taxableAnnual = Math.max(0, basePay - annualHealth - annual401k);

    if (basePay <= 0) {
      return;
    }

    setPitRate(`${getPitEffectiveRate(taxableAnnual)}`);
    setSdiRate(`${STANDARD_SDI_RATE}`);
  }, [annualSalary, hourlyRate, payType, includeHealth, healthAmount, include401k, rate401k]);

  useEffect(() => {
    if (!selectedUserId) {
      setPaystubHistory([]);
      setHistoryYears([]);
      return;
    }
    fetchPaystubHistory(historyYearValue);
  }, [selectedUserId, historyYearValue]);

  const computed = useMemo(() => {
    const warnings: string[] = [];
    const paystubs: PaystubDraft[] = [];
    const payDateInput = parseDate(mostRecentPayDate);
    const count = Math.max(parseInt(paystubCount, 10) || 0, 0);
    const hire = parseDate(hireDate);
    let skipped = 0;

    if (!payDateInput || count === 0) {
      return { warnings, paystubs, skipped };
    }

    if (payDateInput.getDay() !== 5) {
      warnings.push("Most recent pay date is not a Friday. Schedule assumes Friday pay dates.");
    }

    const payDates = Array.from({ length: count }, (_, index) =>
      addDays(payDateInput, -14 * index)
    ).sort((a, b) => a.getTime() - b.getTime());

    const annualSalaryValue = parseNumber(annualSalary);
    const hourlyRateValue = parseNumber(hourlyRate);
    const hoursValue = parseNumber(hoursWorked);
    const annualizedPay =
      payType === "SALARY" ? annualSalaryValue : roundCurrency(hourlyRateValue * 2080);
    const federalRate = getFederalRate(annualizedPay);
    const bonusRate = parseNumber(yearEndBonusRate);

    const buildCurrentLines = (
      payDate: Date,
      bonusAmount: number,
      salaryGrossOverride?: number
    ) => {
      const earningsBase: Array<Omit<EarningsLine, "ytd_amount">> = [];

      if (payType === "SALARY") {
        const baseGross = roundCurrency(annualSalaryValue / 26);
        const gross =
          typeof salaryGrossOverride === "number" ? salaryGrossOverride : baseGross;
        const rate = roundCurrency(annualSalaryValue / 2080);
        earningsBase.push({
          description: "Regular Earnings",
          hours: 80,
          rate,
          current_amount: gross,
        });
        if (bonusAmount > 0) {
          earningsBase.push({
            description: "Year-end Bonus",
            hours: null,
            rate: null,
            current_amount: bonusAmount,
          });
        }
      } else if (payType === "HOURLY") {
        const regularHours = Math.min(hoursValue, 80);
        const overtimeHours = Math.max(0, hoursValue - 80);
        if (regularHours > 0) {
          earningsBase.push({
            description: "Regular Earnings",
            hours: roundCurrency(regularHours),
            rate: roundCurrency(hourlyRateValue),
            current_amount: roundCurrency(regularHours * hourlyRateValue),
          });
        }
        if (overtimeHours > 0) {
          const overtimeRate = roundCurrency(hourlyRateValue * 1.5);
          earningsBase.push({
            description: "Overtime",
            hours: roundCurrency(overtimeHours),
            rate: overtimeRate,
            current_amount: roundCurrency(overtimeHours * overtimeRate),
          });
        }
      } else {
        if (hoursValue > 0) {
          earningsBase.push({
            description: "Contractor Earnings",
            hours: roundCurrency(hoursValue),
            rate: roundCurrency(hourlyRateValue),
            current_amount: roundCurrency(hoursValue * hourlyRateValue),
          });
        }
      }

      const grossPayCurrent = roundCurrency(
        earningsBase.reduce((total, entry) => total + entry.current_amount, 0)
      );
      const preTax401k =
        include401k && payType === "SALARY"
          ? roundCurrency((grossPayCurrent * parseNumber(rate401k)) / 100)
          : 0;
      const preTaxHealth = includeHealth ? roundCurrency(parseNumber(healthAmount)) : 0;
      const preTaxFederal = roundCurrency(preTax401k + preTaxHealth);
      const preTaxFica = preTaxHealth;
      const preTaxSdi = preTaxHealth;

      return {
        earningsBase,
        grossPayCurrent,
        preTaxFederal,
        preTaxFica,
        preTaxSdi,
        deductionsBase: [
          ...(include401k && payType === "SALARY"
            ? [
                {
                  deduction_name: "401(k) Contribution",
                  current_amount: preTax401k,
                },
              ]
            : []),
          ...(includeHealth
            ? [
                {
                  deduction_name: "Health Plan",
                  current_amount: preTaxHealth,
                },
              ]
            : []),
          ...(payType === "CONTRACTOR" && includeContractorFee
            ? [
                {
                  deduction_name: "Contractor Fee",
                  current_amount: roundCurrency(
                    (grossPayCurrent * parseNumber(contractorFeeRate)) / 100
                  ),
                },
              ]
            : []),
        ] as Array<Omit<DeductionLine, "ytd_amount">>,
      };
    };

    const buildYtdForDate = (payDate: Date) => {
      const payDateKey = formatDate(payDate);
      const datesInYear: Date[] = [];
      let cursor = payDate;

      while (cursor.getFullYear() === payDate.getFullYear()) {
        const periodEnd = addDays(cursor, -5);
        if (hire && periodEnd < hire) {
          break;
        }
        datesInYear.push(cursor);
        cursor = addDays(cursor, -14);
      }

      datesInYear.reverse();

      const ytd = {
        gross: 0,
        deductions: 0,
        net: 0,
        pitTaxable: 0,
        earnings: {} as Record<string, number>,
        deductionLines: {} as Record<string, number>,
      };

      let earnings: EarningsLine[] = [];
      let deductions: DeductionLine[] = [];
      let totals: TotalsLine | null = null;
      let leaveBalances: PaystubDraft["leave_balances"] | undefined;

      const salaryPeriodsInYear = datesInYear.length;
      const salaryPerPeriod = annualSalaryValue / 26;
      const salaryPerPeriodRounded = roundCurrency(salaryPerPeriod);
      const salaryTargetTotal = roundCurrency(salaryPerPeriod * salaryPeriodsInYear);
      const salaryPriorTotal = roundCurrency(
        salaryPerPeriodRounded * Math.max(salaryPeriodsInYear - 1, 0)
      );
      const trueUpGross = roundCurrency(salaryTargetTotal - salaryPriorTotal);

      for (const [index, date] of datesInYear.entries()) {
        const periodCount = index + 1;
        const shouldApplyBonus =
          payType === "SALARY" && bonusRate > 0 && isLastPayDateOfYear(date);
        const bonusAmount = shouldApplyBonus
          ? roundCurrency((salaryTargetTotal * bonusRate) / 100)
          : 0;
        const salaryGrossOverride =
          payType === "SALARY" && isLastPayDateOfYear(date) ? trueUpGross : undefined;
        const current = buildCurrentLines(date, bonusAmount, salaryGrossOverride);
        const taxableFederal = Math.max(0, current.grossPayCurrent - current.preTaxFederal);
        const taxableFica = Math.max(0, current.grossPayCurrent - current.preTaxFica);
        const taxableSdi = Math.max(0, current.grossPayCurrent - current.preTaxSdi);
        const deductionsBase = [...current.deductionsBase];

        if (includeFederal && federalRate > 0) {
          deductionsBase.push({
            deduction_name: "Federal Income Tax",
            current_amount: roundCurrency((taxableFederal * federalRate) / 100),
          });
        }
        if (includeSocialSecurity) {
          deductionsBase.push({
            deduction_name: "Social Security",
            current_amount: roundCurrency((taxableFica * parseNumber(ssRate)) / 100),
          });
        }
        if (includeMedicare) {
          deductionsBase.push({
            deduction_name: "Medicare",
            current_amount: roundCurrency((taxableFica * parseNumber(medicareRate)) / 100),
          });
        }
        if (includeSdi) {
          deductionsBase.push({
            deduction_name: "State Disability (SDI)",
            current_amount: roundCurrency((taxableSdi * parseNumber(sdiRate)) / 100),
          });
        }

        if (includePit) {
          const pitTotalBefore = calculatePitTax(ytd.pitTaxable);
          const pitTotalAfter = calculatePitTax(ytd.pitTaxable + taxableFederal);
          const pitCurrent = Math.max(0, pitTotalAfter - pitTotalBefore);
          deductionsBase.push({
            deduction_name: "State Income Tax (PIT)",
            current_amount: roundCurrency(pitCurrent),
          });
          ytd.pitTaxable = roundCurrency(ytd.pitTaxable + taxableFederal);
        }

        const totalDeductionsCurrent = roundCurrency(
          deductionsBase.reduce((total, entry) => total + entry.current_amount, 0)
        );
        const netPayCurrent = roundCurrency(current.grossPayCurrent - totalDeductionsCurrent);

        const earningsWithYtd = current.earningsBase.map((entry) => {
          const previous = ytd.earnings[entry.description] || 0;
          const next = roundCurrency(previous + entry.current_amount);
          ytd.earnings[entry.description] = next;
          return { ...entry, ytd_amount: next };
        });

        const deductionsWithYtd = deductionsBase.map((entry) => {
          const previous = ytd.deductionLines[entry.deduction_name] || 0;
          const next = roundCurrency(previous + entry.current_amount);
          ytd.deductionLines[entry.deduction_name] = next;
          return { ...entry, ytd_amount: next };
        });

        ytd.gross = roundCurrency(ytd.gross + current.grossPayCurrent);
        ytd.deductions = roundCurrency(ytd.deductions + totalDeductionsCurrent);
        ytd.net = roundCurrency(ytd.net + netPayCurrent);

        if (formatDate(date) === payDateKey) {
          earnings = earningsWithYtd;
          deductions = deductionsWithYtd;
          totals = {
            gross_pay_current: current.grossPayCurrent,
            total_deductions_current: totalDeductionsCurrent,
            net_pay_current: netPayCurrent,
            gross_pay_ytd: ytd.gross,
            total_deductions_ytd: ytd.deductions,
            net_pay_ytd: ytd.net,
          };
          if (payType === "SALARY") {
            const vacationAccrued = roundCurrency(
              Math.min(VACATION_CAP, VACATION_ACCRUAL_PER_PERIOD * periodCount)
            );
            const sickAccrued = roundCurrency(
              Math.min(SICK_CAP, SICK_ACCRUAL_PER_PERIOD * periodCount)
            );
            leaveBalances = {
              vacation_accrued: vacationAccrued,
              vacation_used: 0,
              vacation_balance: vacationAccrued,
              sick_accrued: sickAccrued,
              sick_used: 0,
              sick_balance: sickAccrued,
            };
          }
        }
      }

      if (!totals) {
        return null;
      }

      return { earnings, deductions, totals, leaveBalances };
    };

    for (const payDate of payDates) {
      const payPeriodEnd = addDays(payDate, -5);
      const payPeriodStart = addDays(payPeriodEnd, -13);

      if (hire && payPeriodEnd < hire) {
        skipped += 1;
        continue;
      }

      const ytdPayload = buildYtdForDate(payDate);
      if (!ytdPayload) {
        continue;
      }

      paystubs.push({
        pay_date: formatDate(payDate),
        pay_period_start: formatDate(payPeriodStart),
        pay_period_end: formatDate(payPeriodEnd),
        earnings: ytdPayload.earnings,
        deductions: ytdPayload.deductions,
        totals: ytdPayload.totals,
        leave_balances: ytdPayload.leaveBalances,
      });
    }

    if (skipped > 0) {
      warnings.push(`Skipped ${skipped} pay period(s) before the hire date.`);
    }

    return { warnings, paystubs, skipped };
  }, [
    mostRecentPayDate,
    paystubCount,
    hireDate,
    payType,
    annualSalary,
    hourlyRate,
    hoursWorked,
    includeFederal,
    includeSocialSecurity,
    includeMedicare,
    includePit,
    includeSdi,
    includeHealth,
    include401k,
    includeContractorFee,
    ssRate,
    medicareRate,
    pitRate,
    sdiRate,
    healthAmount,
    contractorFeeRate,
    yearEndBonusRate,
    rate401k,
  ]);

  const fetchPaystubHistory = async (year?: number) => {
    if (!selectedUserId) {
      return;
    }
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const data = (await listPaystubsForUser(
        Number(selectedUserId),
        year
      )) as PaystubListResponse;
      setPaystubHistory(data.items);
      setHistoryYears(data.available_years);
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "Unable to load paystubs");
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleHistoryDownload = async (stub: PaystubSummary) => {
    setHistoryError(null);
    try {
      const { blob, filename } = await downloadPaystubPdf(stub.id);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename || stub.file_name || "paystub.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "Unable to download paystub");
    }
  };

  const handleDeletePaystub = async (stub: PaystubSummary) => {
    const confirmed = window.confirm(
      `Delete paystub dated ${stub.pay_date}? This cannot be undone.`
    );
    if (!confirmed) {
      return;
    }
    setHistoryError(null);
    try {
      await deletePaystub(stub.id);
      await fetchPaystubHistory(historyYearValue);
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "Unable to delete paystub");
    }
  };

  const handleUploadPaystub = async () => {
    if (!selectedUserId) {
      setUploadError("Select an employee before uploading.");
      return;
    }
    if (!uploadFile) {
      setUploadError("Select a PDF file to upload.");
      return;
    }
    if (!uploadPayDate || !uploadPeriodStart || !uploadPeriodEnd) {
      setUploadError("Complete all pay period dates.");
      return;
    }
    setUploadError(null);
    setUploading(true);
    try {
      await uploadPaystub({
        userId: Number(selectedUserId),
        pay_date: uploadPayDate,
        pay_period_start: uploadPeriodStart,
        pay_period_end: uploadPeriodEnd,
        file: uploadFile,
        file_name: uploadFileName || null,
      });
      setUploadPayDate("");
      setUploadPeriodStart("");
      setUploadPeriodEnd("");
      setUploadFileName("");
      setUploadFile(null);
      await fetchPaystubHistory(historyYearValue);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Unable to upload paystub");
    } finally {
      setUploading(false);
    }
  };

  const handleGenerate = async () => {
    setError(null);
    setStatus(null);

    if (!employeeName || !jobTitle || !department) {
      setError("Select an employee and confirm the job title and department.");
      return;
    }
    if (!mostRecentPayDate || !paystubCount || computed.paystubs.length === 0) {
      setError("Add a valid pay date and the number of paystubs to generate.");
      return;
    }
    if (payType === "SALARY" && parseNumber(annualSalary) <= 0) {
      setError("Enter an annual salary greater than 0.");
      return;
    }
    if (payType !== "SALARY" && parseNumber(hourlyRate) <= 0) {
      setError("Enter an hourly rate greater than 0.");
      return;
    }
    if (payType !== "SALARY" && parseNumber(hoursWorked) <= 0) {
      setError("Enter hours worked for the pay period.");
      return;
    }

    const selected = users.find((entry) => `${entry.id}` === selectedUserId);
    if (!selected) {
      setError("Select an employee to continue.");
      return;
    }

    const payTypeValue = payType === "SALARY" ? "Salary" : "Hourly";
    const employmentTypeValue = payType === "CONTRACTOR" ? "Contractor" : employmentType;

    setIsGenerating(true);
    setProgress({ current: 0, total: computed.paystubs.length });

    try {
      for (const [index, paystub] of computed.paystubs.entries()) {
        const payDateObj = parseDate(paystub.pay_date);
        if (!payDateObj) {
          continue;
        }
        const payload = {
          company: {
            company_name: "Kyronix LLC",
            company_logo_url: companyLogoUrl || null,
            company_address: companyAddress,
            payroll_contact_email: payrollEmail,
          },
          employee: {
            employee_id: employeeId || `${selected.id}`,
            employee_name: employeeName,
            job_title: jobTitle,
            department,
            employment_type: employmentTypeValue,
            pay_type: payTypeValue,
            pay_rate: payType === "SALARY" ? parseNumber(annualSalary) : parseNumber(hourlyRate),
          },
          pay_period: {
            pay_period_start: paystub.pay_period_start,
            pay_period_end: paystub.pay_period_end,
            pay_date: paystub.pay_date,
            pay_frequency: "Bi-Weekly",
          },
          earnings: paystub.earnings,
          deductions: paystub.deductions,
          totals: paystub.totals,
          payment: {
            payment_method: paymentMethod,
            bank_name_masked: bankMasked,
            payment_status: paymentStatus,
          },
          metadata: {
            paystub_id: `ps_${employeeId || selected.id}_${formatCompactDate(payDateObj)}`,
            generated_timestamp: new Date().toISOString(),
          },
          leave_balances: paystub.leave_balances ?? null,
        };

        const { blob, filename } = await generatePaystubPdf(payload);
        const downloadName = filename || buildFileName(employeeName, payDateObj);
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = downloadName;
        link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);

        setProgress({ current: index + 1, total: computed.paystubs.length });
      }
      setStatus("Paystubs generated and downloaded.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to generate paystubs.");
    } finally {
      setIsGenerating(false);
    }
  };

  const annualSalaryValue = parseNumber(annualSalary);
  const hourlyRateValue = parseNumber(hourlyRate);
  const annualizedPay =
    payType === "SALARY" ? annualSalaryValue : roundCurrency(hourlyRateValue * 2080);
  const federalRate = getFederalRate(annualizedPay);

  return (
    <>
      {error && <div className="card">{error}</div>}
      {historyError && <div className="card">{historyError}</div>}
      {uploadError && <div className="card">{uploadError}</div>}
      {status && <div className="card">{status}</div>}
      {computed.warnings.length > 0 && (
        <div className="card">
          <strong>Notes</strong>
          <ul>
            {computed.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="card">
        <h2 style={{ marginTop: 0 }}>Paystub Builder</h2>
        <p style={{ marginTop: 6, color: "rgba(11, 31, 42, 0.6)" }}>
          Generate paystubs from standardized rules. All files are produced as PDFs.
        </p>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Employee details</h3>
        <div className="grid">
          <select
            className="input"
            value={selectedUserId}
            onChange={(event) => setSelectedUserId(event.target.value)}
          >
            <option value="">Select employee</option>
            {users.map((user) => (
              <option key={user.id} value={user.id}>
                {`${user.legal_first_name} ${user.legal_last_name} - ${user.email}`}
              </option>
            ))}
          </select>
          <div className="row">
            <input
              className="input"
              placeholder="Employee ID (internal only)"
              value={employeeId}
              onChange={(event) => setEmployeeId(event.target.value)}
            />
            <input
              className="input"
              placeholder="Employee name"
              value={employeeName}
              onChange={(event) => setEmployeeName(event.target.value)}
            />
          </div>
          <div className="row">
            <input
              className="input"
              placeholder="Job title"
              value={jobTitle}
              onChange={(event) => setJobTitle(event.target.value)}
            />
            <input
              className="input"
              placeholder="Department"
              value={department}
              onChange={(event) => setDepartment(event.target.value)}
            />
          </div>
          <div className="row">
            <select
              className="input"
              disabled={payType === "CONTRACTOR"}
              value={payType === "CONTRACTOR" ? "Contractor" : employmentType}
              onChange={(event) =>
                setEmploymentType(event.target.value as "Full-Time" | "Part-Time")
              }
            >
              <option value="Full-Time">Full-Time</option>
              <option value="Part-Time">Part-Time</option>
              {payType === "CONTRACTOR" && <option value="Contractor">Contractor</option>}
            </select>
            <label style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
              Hire date
              <input
                className="input"
                type="date"
                value={hireDate}
                onChange={(event) => setHireDate(event.target.value)}
              />
            </label>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h3 style={{ marginTop: 0 }}>Paystub history</h3>
            <p style={{ marginTop: 6, color: "rgba(11, 31, 42, 0.6)" }}>
              Review uploaded and generated paystubs for the selected employee.
            </p>
          </div>
          <div className="row" style={{ alignItems: "center" }}>
            <label style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
              Year
              <select
                className="input"
                style={{ marginLeft: 8 }}
                value={historyYear}
                onChange={(event) => setHistoryYear(event.target.value)}
                disabled={!selectedUserId}
              >
                <option value="all">All years</option>
                {historyYears.map((year) => (
                  <option key={year} value={String(year)}>
                    {year}
                  </option>
                ))}
              </select>
            </label>
            <button
              className="button secondary"
              onClick={() => fetchPaystubHistory(historyYearValue)}
              disabled={!selectedUserId || historyLoading}
            >
              Refresh
            </button>
          </div>
        </div>
        {!selectedUserId ? (
          <p>Select an employee to view paystubs.</p>
        ) : historyLoading ? (
          <p>Loading paystubs...</p>
        ) : paystubHistory.length === 0 ? (
          <p>No paystubs available.</p>
        ) : (
          <div className="grid">
            {paystubHistory.map((stub) => (
              <div key={stub.id} className="card" style={{ padding: 16 }}>
                <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <strong>{`Pay date: ${stub.pay_date}`}</strong>
                    <div style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                      {`Pay period: ${stub.pay_period_start} to ${stub.pay_period_end}`}
                    </div>
                  </div>
                  <div className="row">
                    <button className="button secondary" onClick={() => handleHistoryDownload(stub)}>
                      Download
                    </button>
                    <button
                      className="button secondary"
                      style={{ borderColor: "rgba(154, 74, 20, 0.4)", color: "#9a4a14" }}
                      onClick={() => handleDeletePaystub(stub)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Upload paystub PDF</h3>
        <p style={{ marginTop: 6, color: "rgba(11, 31, 42, 0.6)" }}>
          Attach an existing PDF to the selected employee.
        </p>
        <div className="grid">
          <input
            className="input"
            type="file"
            accept="application/pdf"
            onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
          />
          <div className="row">
            <label style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
              Pay period start
              <input
                className="input"
                type="date"
                value={uploadPeriodStart}
                onChange={(event) => setUploadPeriodStart(event.target.value)}
              />
            </label>
            <label style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
              Pay period end
              <input
                className="input"
                type="date"
                value={uploadPeriodEnd}
                onChange={(event) => setUploadPeriodEnd(event.target.value)}
              />
            </label>
          </div>
          <label style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
            Pay date
            <input
              className="input"
              type="date"
              value={uploadPayDate}
              onChange={(event) => setUploadPayDate(event.target.value)}
            />
          </label>
          <input
            className="input"
            placeholder="File name (optional)"
            value={uploadFileName}
            onChange={(event) => setUploadFileName(event.target.value)}
          />
          <button
            className="button"
            onClick={handleUploadPaystub}
            disabled={!selectedUserId || uploading}
          >
            {uploading ? "Uploading..." : "Upload paystub"}
          </button>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Pay rules</h3>
        <div className="grid">
          <div className="row">
            <select
              className="input"
              value={payType}
              onChange={(event) => setPayType(event.target.value as PayType)}
            >
              <option value="SALARY">Salary</option>
              <option value="HOURLY">Hourly</option>
              <option value="CONTRACTOR">Contractor</option>
            </select>
            <label style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
              Most recent pay date
              <input
                className="input"
                type="date"
                value={mostRecentPayDate}
                onChange={(event) => setMostRecentPayDate(event.target.value)}
              />
            </label>
          </div>
          <div className="row">
            <input
              className="input"
              placeholder="Number of paystubs to generate"
              type="number"
              min="1"
              value={paystubCount}
              onChange={(event) => setPaystubCount(event.target.value)}
            />
            <input className="input" value="Bi-Weekly (Mon-Sun)" readOnly />
          </div>

          {payType === "SALARY" && (
            <div className="row">
              <label style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                Annual salary
                <input
                  className="input"
                  type="number"
                  value={annualSalary}
                  onChange={(event) => setAnnualSalary(event.target.value)}
                />
              </label>
              <label style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                Standard hours per pay period
                <input className="input" value="80" readOnly />
              </label>
            </div>
          )}

          {payType !== "SALARY" && (
            <div className="row">
              <input
                className="input"
                placeholder="Hourly rate"
                type="number"
                value={hourlyRate}
                onChange={(event) => setHourlyRate(event.target.value)}
              />
              <input
                className="input"
                placeholder="Hours worked (per pay period)"
                type="number"
                value={hoursWorked}
                onChange={(event) => setHoursWorked(event.target.value)}
              />
            </div>
          )}

          {payType === "SALARY" && (
            <div className="row">
              <label style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                Year-end bonus rate (%)
                <input
                  className="input"
                  type="number"
                  value={yearEndBonusRate}
                  onChange={(event) => setYearEndBonusRate(event.target.value)}
                />
              </label>
              <label style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                Bonus timing
                <input
                  className="input"
                  value="Last pay date of the year (based on actual salary earned)"
                  readOnly
                />
              </label>
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Deductions</h3>
        <div className="grid">
          <label className="row" style={{ alignItems: "center" }}>
            <input
              type="checkbox"
              checked={includeFederal}
              onChange={(event) => setIncludeFederal(event.target.checked)}
              disabled={payType === "CONTRACTOR"}
            />
            Federal Income Tax ({federalRate}%)
          </label>
          <div className="row">
            <label className="row" style={{ alignItems: "center" }}>
              <input
                type="checkbox"
                checked={includeSocialSecurity}
                onChange={(event) => setIncludeSocialSecurity(event.target.checked)}
                disabled={payType === "CONTRACTOR"}
              />
              Social Security (%)
            </label>
            <input
              className="input"
              type="number"
              value={ssRate}
              onChange={(event) => setSsRate(event.target.value)}
              disabled={!includeSocialSecurity || payType === "CONTRACTOR"}
            />
          </div>
          <div className="row">
            <label className="row" style={{ alignItems: "center" }}>
              <input
                type="checkbox"
                checked={includeMedicare}
                onChange={(event) => setIncludeMedicare(event.target.checked)}
                disabled={payType === "CONTRACTOR"}
              />
              Medicare (%)
            </label>
            <input
              className="input"
              type="number"
              value={medicareRate}
              onChange={(event) => setMedicareRate(event.target.value)}
              disabled={!includeMedicare || payType === "CONTRACTOR"}
            />
          </div>
          <div className="row">
            <label className="row" style={{ alignItems: "center" }}>
              <input
                type="checkbox"
                checked={includePit}
                onChange={(event) => setIncludePit(event.target.checked)}
                disabled={payType === "CONTRACTOR"}
              />
              State Income Tax (PIT) - CA 2026 Single (progressive)
            </label>
            <input
              className="input"
              type="number"
              value={pitRate}
              onChange={(event) => setPitRate(event.target.value)}
              readOnly
              disabled={!includePit || payType === "CONTRACTOR"}
            />
          </div>
          <div className="row">
            <label className="row" style={{ alignItems: "center" }}>
              <input
                type="checkbox"
                checked={includeSdi}
                onChange={(event) => setIncludeSdi(event.target.checked)}
                disabled={payType === "CONTRACTOR"}
              />
              State Disability (SDI) (%)
            </label>
            <input
              className="input"
              type="number"
              value={sdiRate}
              onChange={(event) => setSdiRate(event.target.value)}
              disabled={!includeSdi || payType === "CONTRACTOR"}
            />
          </div>
          <div className="row">
            <label className="row" style={{ alignItems: "center" }}>
              <input
                type="checkbox"
                checked={includeHealth}
                onChange={(event) => setIncludeHealth(event.target.checked)}
                disabled={payType === "CONTRACTOR"}
              />
              Health Plan (per pay period)
            </label>
            <input
              className="input"
              type="number"
              value={healthAmount}
              onChange={(event) => setHealthAmount(event.target.value)}
              disabled={!includeHealth || payType === "CONTRACTOR"}
            />
          </div>
          {payType === "SALARY" && (
            <div className="row">
              <label className="row" style={{ alignItems: "center" }}>
                <input
                  type="checkbox"
                  checked={include401k}
                  onChange={(event) => setInclude401k(event.target.checked)}
                />
                401(k) Contribution (% of gross, match noted)
              </label>
              <input
                className="input"
                type="number"
                value={rate401k}
                onChange={(event) => setRate401k(event.target.value)}
                disabled={!include401k}
              />
            </div>
          )}
          {payType === "CONTRACTOR" && (
            <div className="row">
              <label className="row" style={{ alignItems: "center" }}>
                <input
                  type="checkbox"
                  checked={includeContractorFee}
                  onChange={(event) => setIncludeContractorFee(event.target.checked)}
                />
                Contractor fee (%)
              </label>
              <input
                className="input"
                type="number"
                value={contractorFeeRate}
                onChange={(event) => setContractorFeeRate(event.target.value)}
                disabled={!includeContractorFee}
              />
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Payment + company details</h3>
        <div className="grid">
          <div className="row">
            <label style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
              Payment method
              <select
                className="input"
                value={paymentMethod}
                onChange={(event) =>
                  setPaymentMethod(event.target.value as "Direct Deposit" | "Check")
                }
              >
                <option value="Direct Deposit">Direct Deposit</option>
                <option value="Check">Check</option>
              </select>
            </label>
            <label style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
              Payment status
              <input
                className="input"
                value={paymentStatus}
                onChange={(event) => setPaymentStatus(event.target.value)}
              />
            </label>
          </div>
          <label style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
            Bank name (masked)
            <input
              className="input"
              value={bankMasked}
              onChange={(event) => setBankMasked(event.target.value)}
            />
          </label>
          <div className="row">
            <label style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
              Company address
              <input
                className="input"
                value={companyAddress}
                onChange={(event) => setCompanyAddress(event.target.value)}
              />
            </label>
            <label style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
              Payroll contact email
              <input
                className="input"
                type="email"
                value={payrollEmail}
                onChange={(event) => setPayrollEmail(event.target.value)}
              />
            </label>
          </div>
          <label style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
            Company logo URL (optional)
            <input
              className="input"
              value={companyLogoUrl}
              onChange={(event) => setCompanyLogoUrl(event.target.value)}
            />
          </label>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Preview</h3>
        {computed.paystubs.length === 0 && <p>No paystubs ready to generate yet.</p>}
        {computed.paystubs.length > 0 && (
          <div className="grid">
            {computed.paystubs.map((stub) => (
              <div key={stub.pay_date} className="row" style={{ justifyContent: "space-between" }}>
                <div>
                  <strong>{stub.pay_date}</strong>
                  <div style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                    {`${stub.pay_period_start} to ${stub.pay_period_end}`}
                  </div>
                  {stub.leave_balances && (
                    <div style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                      {`Vacation: ${stub.leave_balances.vacation_balance.toFixed(
                        2
                      )} hrs, Sick: ${stub.leave_balances.sick_balance.toFixed(2)} hrs`}
                    </div>
                  )}
                </div>
                <div>{formatCurrency(stub.totals.gross_pay_current)}</div>
                <div>{formatCurrency(stub.totals.net_pay_current)}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <strong>Generate paystubs</strong>
            <div style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
              {progress.total > 0
                ? `${progress.current}/${progress.total} complete`
                : "Ready to generate."}
            </div>
          </div>
          <button className="button" onClick={handleGenerate} disabled={isGenerating}>
            {isGenerating ? "Generating..." : "Generate PDFs"}
          </button>
        </div>
      </div>
    </>
  );
}
