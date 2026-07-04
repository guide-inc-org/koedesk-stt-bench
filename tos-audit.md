# STTベンチマーク公開 事前確認 — 各社ToS/データセットライセンス監査（ドラフト）

**作成日**: 2026-07-04
**調査範囲**: koedeskが主要STT APIを言語別に実測し、結果をリーダーボード＋記事として公開する計画に対する、各社利用規約上の制約の事前整理
**アクセス日**: 記載がない限りすべて2026-07-04

> **免責**: 本書は法律アドバイスではない。公開されている一次規約の原文を調査担当（Claude）が検索・引用して整理した事実整理メモであり、契約解釈・リスク許容度の最終判断は法務確認を経ること。特に「⚠️条件付き」「❓要追加確認」の項目は、実際にベンチマークを実施・公開する前に必ず一次資料を人間が再確認すること。

---

## 1. サマリ表

| # | プロバイダ | 対象サービス | 判定 | 根拠（一言） |
|---|-----------|------------|------|------------|
| 1 | ElevenLabs | Scribe STT API | ✅ 公開可 | ToS本体・Speech to Text専用条項のいずれにもベンチマーク/競合分析の禁止条項なし |
| 2 | OpenAI | gpt-4o-transcribe / whisper-1 API | ✅ 公開可 | Terms of Use・Usage Policies・Services Agreementのいずれにもベンチマーク禁止条項なし（Output流用による競合モデル開発の禁止条項はあるが、精度計測公開とは別問題） |
| 3 | Whisper large-v3（OSS） | ローカル推論 | ✅ 公開可 | MITライセンス（改変・再頒布・商用利用ともに無制限、著作権表示のみ必須） |
| 4 | Google Cloud Speech-to-Text v2 | GCP | ⚠️ 条件付き | Service Specific Terms 第7条「Benchmarking」で結果再現に必要な情報の完全開示＋Googleへの相互ベンチマーク許諾が公開の条件。ハイパースケール・クラウド事業者の代理としてのテストのみ事前同意必須（koedeskは非該当） |
| 5 | Gemini API（音声入力） | Gemini API | ✅ 公開可（要再確認） | Gemini API Additional ToSにベンチマーク条項なし。Google APIs Terms of Service（developers.google.com/terms）にも同条項なし |
| 6 | Deepgram | Nova-3 | ✅ 公開可（要再確認） | 一般ToS・Business ToS PDF・旧Terms of Use PDFのいずれにもベンチマーク条項見つからず。ただしOCR精度に限界ありPDFにつき要目視再確認 |
| 7 | AssemblyAI | Universal | ❌ 禁止 | Terms of Service 2.4(f)で「competitive analysis or benchmarking」への使用を明示的に禁止。**実施自体がToS違反になり得る最重要リスク** |
| 8 | AmiVoice API（国産） | AmiVoice API | ✅ 公開可 | 利用規約（docs.amivoice.com）にベンチマーク・性能比較・競合分析の禁止条項なし |
| 9 | Azure AI Speech（候補） | Cognitive Services Speech | ⚠️ 条件付き | Microsoft Product Terms（Universal License Terms for Online Services）に「Competitive Benchmarking」条項。事前同意は不要だが、koedeskが「競合製品」に該当する場合、Microsoftの請求に応じて再現情報の提供＋Microsoftによる反対ベンチマーク実施への協力義務が発生 |
| 10 | Speechmatics（候補） | STT API | ✅ 公開可（要再確認） | Terms of Serviceにベンチマーク条項見つからず。むしろ自社ブログで他社比較ベンチマーク手法を公開しており、比較文化に寛容な可能性 |
| 11 | xAI | Grok Speech-to-Text (`/v1/stt`) | ❌ **禁止 → 除外（2026-07-04 maintainer decision）** | Enterprise Customer Agreement（API利用に適用・GSA承認版 June 2025 原文で確認）の禁止行為 **(j)項**: "use or permit the use of any tools in order to probe, scan or attempt to penetrate or **benchmark** any Services"。probe/scan/penetrateと並置でセキュリティ試験文脈と読む余地はあるが、"benchmark"が禁止リストに明記されている以上、AssemblyAI 2.4(f)と同基準で除外が整合。書面同意が得られればv1.1で追加可 |
| 12 | Microsoft（MAI） | MAI-Transcribe-1.5（Azure Speech LLM Speech API 経由・2026-07-05 追加監査） | ⚠️ 条件付き | Microsoft first-party モデル＝#9 と同一の Product Terms「Competitive Benchmarking」条項（相互主義のみ・禁止なし・事前同意不要）が適用。MAI 固有の追加規約・AUP は不在。API は public preview（Preview 補足規約にもベンチ制限なし）。詳細 §2.11 |

**判定内訳**: ✅公開可 6／⚠️条件付き 3／❌禁止 2／❓要追加確認 1（下記「未確認事項」参照）

**特に危険な条項を持つプロバイダ**: **AssemblyAI**（ToS 2.4(f)で競合分析・ベンチマーク自体を明示的に禁止。公開の可否以前に、実測（API呼び出し）そのものが契約違反になり得る）と**xAI**（ECA (j)項に"benchmark"明記→除外決定）。次点で**Google Cloud**と**Microsoft Azure**（禁止ではないが、公開時に相手方への相互ベンチマーク機会付与や情報開示という「条件」が付く）。

**⚠️手順の教訓（2026-07-04）**: xAIはR-2.1の建付け（測定前に監査）に反して**パイロット実行後に規約を確認した**。パイロットデータは非公開のまま内部保管・数値は一切公表しない。以後、新エンジン追加時は「規約監査→実測」の順序を厳守する（AmiVoiceは事前監査済みで問題なし）。

---

## 2. 各社詳細

### 2.1 ElevenLabs（Scribe STT API）
- **文書**: [Terms of Service (non-EEA)](https://elevenlabs.io/terms-of-use)、[Service-Specific Terms](https://elevenlabs.io/service-specific-terms)、[Speech to Text Terms](https://elevenlabs.io/speech-to-text-terms)
- **アクセス日**: 2026-07-04
- **原文引用（Section 2, Personal Data）**:
  > "You acknowledge that ElevenLabs may process personal data relating to the operation, support, or use of our Services for our own business purposes, such as billing, account management, data analysis, **benchmarking**, technical support, product development, research and development of its AI models, improvement of its systems and technologies, and compliance with law."
  - これは「ElevenLabs自身が内部的にベンチマークを行う」ことを許容する条項であり、**ユーザー側がベンチマークを実施・公開することを制限する条項ではない**。
- **Speech to Text Terms**: 章立ては「SPEECH TO TEXT」「AUTOMATED FEATURES」「MODEL-SPECIFIC TERMS」のみで、ベンチマーク・競合分析・reverse engineer・competing service等のキーワードを含む条項は不在。
- **主ToS本体**でも "competitive" "competing" "competitor" "reverse engineer" "similar service" を含む条項は不在（再検索で確認）。
- **判定**: ✅ 公開可
- **根拠**: 3つの関連文書いずれにもユーザーによるベンチマーク実施・結果公開を制限する条項が見当たらない。

### 2.2 OpenAI（gpt-4o-transcribe / whisper-1 API）
- **文書**: [Terms of Use](https://openai.com/policies/row-terms-of-use/)（403のためr.jina.ai経由で取得）、[Usage Policies](https://openai.com/policies/usage-policies/)、[Services Agreement](https://openai.com/policies/services-agreement/)（API事業者向け契約）
- **アクセス日**: 2026-07-04
- **Terms of Use**: 章立ては Who we are / Registration and access / Using our Services / Content / Our IP rights / Paid accounts / Termination and suspension / Discontinuation of Services / Disclaimer of warranties / Limitation of liability / Indemnity / Dispute resolution / Copyright complaints / General Terms。ベンチマーク関連条項なし。
- **Usage Policies**: 章立ては Protect people / Respect privacy / Keep minors safe / Empower people / Changelog。該当条項なし。
- **Services Agreement 第3.3条（Restrictions）原文引用**:
  > "except for a Permitted Exception, use Output to develop artificial intelligence models that compete with OpenAI's products and services"
  - これは「APIのOutputを使って競合AIモデルを開発すること」を禁じる条項であり、**精度を測定して結果を公開する行為そのものを禁じる条項ではない**。koedeskの計画（文字起こし精度の測定・公開）はモデル開発を伴わないため、この条項には抵触しない。
- **判定**: ✅ 公開可
- **根拠**: 3文書いずれにも直接のベンチマーク禁止条項なし。唯一近い条項（3.3条）は「Output流用によるモデル開発」の禁止であり、ベンチマーク結果公開とは別の論点。

### 2.3 Whisper large-v3（ローカルOSS）
- **文書**: [openai/whisper LICENSE](https://github.com/openai/whisper/blob/main/LICENSE)
- **アクセス日**: 2026-07-04
- **ライセンス種別**: MIT License（Copyright (c) 2022 OpenAI）
- **原文引用**:
  > "Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software..."
- **判定**: ✅ 公開可
- **根拠**: MITは改変・再頒布・商用利用を無制限に許可する最も寛容なOSSライセンス。ベンチマーク実施・結果公開に一切制約なし（著作権表示の保持のみ必須）。

### 2.4 Google Cloud Speech-to-Text v2
- **文書**: [Google Cloud Platform Service Specific Terms](https://cloud.google.com/terms/service-terms)
- **アクセス日**: 2026-07-04
- **原文引用（第7条 Benchmarking）**:
  > "7. Benchmarking. Customer may itself (but may not permit a third party to): (a) conduct benchmark tests of the Services (each a "Test"); and (b) publicly disclose the results of such Tests only if (i) the public disclosure includes all necessary information to replicate the Tests, and (ii) Customer allows Google to conduct benchmark tests of Customer's publicly available products or services and publicly disclose the results of such tests. Notwithstanding the foregoing, Customer may not do either of the following on behalf of a hyperscale public cloud provider without Google's prior written consent: (A) conduct (directly or through a third party) any Test or (B) disclose the results of any such Test."
- **判定**: ⚠️ 条件付き公開可
- **根拠**: 事前同意は不要だが、公開する場合は(i)再現に必要な情報を全て開示すること、(ii)Googleが koedesk の公開製品・サービスに対して同様にベンチマークを実施し結果を公開することを許容すること、の2条件を満たす必要がある。「ハイパースケール・パブリッククラウド事業者の代理として」実施・開示する場合のみ事前の書面同意が必要だが、koedeskはこれに該当しないため通常は事前同意不要。**ただし条件(ii)により、Googleからkoedesk自体への逆ベンチマークを拒否できない点は認識しておく必要がある。**

### 2.5 Gemini API（音声入力）
- **文書**: [Gemini API Additional Terms of Service](https://ai.google.dev/gemini-api/terms)、[Google APIs Terms of Service](https://developers.google.com/terms)
- **アクセス日**: 2026-07-04
- **Gemini API Additional ToS**: 章立ては Age Requirements / Use Restrictions / Use of Generated Content / Unpaid Services / Paid Services / Agentic Services / Grounding with Google Search / Grounding with Google Maps / Hardware Safety / Disclaimers。ベンチマーク関連条項なし。
- **Google APIs Terms of Service**: "benchmark" "benchmarking" "performance testing" "publishing test results" のいずれの語も本文に見当たらず。
- **判定**: ✅ 公開可（要再確認）
- **根拠**: 2文書とも該当条項なし。ただし本調査はキーワード検索ベースであり、Gemini APIはGCPのService Specific Terms（2.4のGCP Benchmarking条項）が適用範囲に含まれるか否かは条文上明示されていない。Gemini APIは別ドメイン（ai.google.dev）で独自ToSを持つため、GCPのBenchmarking条項が及ぶかは❓要追加確認（下記参照）。

### 2.6 Deepgram（Nova-3）
- **文書**: [Terms of Service](https://deepgram.com/terms)、[Business Terms of Service (PDF, 2024-03)](https://static.deepgram.com/business/Business_TOS.pdf)、[Terms of Use (PDF)](https://static.deepgram.com/legal/DeepgramTermsofUse6717.pdf)
- **アクセス日**: 2026-07-04
- **Webサイト版ToS**: 章立ては Copyright / Trademarks / Age of Users / Privacy / Illegal & Unpermitted Activities / Links; Offerings / Indemnification / Disclaimer of Warranties / Limitation of Liability / Changes to Site / Changes to Terms of Use / Applicable Law, Jurisdiction and Claims / Termination / Force Majeure / Copyright Complaints / Notice / General Provisions。該当条項なし。
- **Business ToS PDF・Terms of Use PDF**: いずれもベンチマーク・性能比較・競合分析に関する条項見つからず。
- **判定**: ✅ 公開可（要再確認）
- **根拠**: 3文書とも該当条項なし。**ただしPDF2本はOCR/構造解析に頼った自動読み取りであり、圧縮・スキャン起因で見落としがある可能性を否定できない。実際にDeepgramを使う契約（Order Form含む個別契約）を締結する段階で、その契約書に別途ベンチマーク条項が挿入されていないか目視確認が必要。**

### 2.7 AssemblyAI（Universal）
- **文書**: [Terms of Service](https://www.assemblyai.com/legal/terms-of-service)
- **アクセス日**: 2026-07-04
- **原文引用（Section 2.4(f)）**:
  > "use or access the Services to develop a product or service that is competitive with any AssemblyAI product or service, or engage in competitive analysis or **benchmarking**"
- **関連条項（Section 2.4(i)）**:
  > 顧客または第三者が、Outputを用いて他の音声認識モデルの機能・性能を開発・訓練・最適化・改善することを禁止する条項
- **判定**: ❌ 禁止
- **根拠**: Section 2.4(f)は「competitive analysis or benchmarking」への使用そのものを明示的に禁止しており、公開の可否以前に**AssemblyAIのAPIに対してベンチマーク用の音声を投げて精度を測定する行為自体がToS違反となる**。他社と異なり「公開時の条件」ではなく「実施自体の禁止」である点が最大のリスク。koedeskの計画通りにAssemblyAIを含めて実測・公開する場合、事前にAssemblyAIから書面の許諾を得るか、対象から除外する必要がある。

### 2.8 AmiVoice API（国産・アドバンスト・メディア）
- **文書**: [AmiVoice API 利用規約](https://docs.amivoice.com/amivoice-api/legal/terms)（旧URL https://acp.amivoice.com/amivoice_api/terms/ から301リダイレクト）
- **アクセス日**: 2026-07-04
- **調査結果**: ベンチマーク・性能評価・比較結果公表・第三者比較・競合分析に関する明示的な条項は不在。
- **近い条項（第11条第1項第4号、禁止行為）原文引用**:
  > 「本サービスの利用又は提供を妨げる行為（事前通知なく実施する負荷テスト、DDoSシミュレーションテスト等を含みますがこれらに限るものではありません）」
  - これは無通知の負荷テスト・DDoS的な行為を禁じるものであり、**通常のAPI呼び出しによる精度測定（負荷をかけない範囲）には該当しない**。
- **秘密保持（第19条）**: 契約者提供情報の取扱いに関する条項であり、ベンチマーク公表の禁止とは無関係。
- **判定**: ✅ 公開可
- **根拠**: 明示的な禁止条項なし。ただし念のため大量リクエストによる負荷テストにならない実施設計（レート制限順守）が必要。

### 2.9 Azure AI Speech（候補）
- **文書**: [Microsoft Product Terms — Universal License Terms For Online Services](https://www.microsoft.com/licensing/terms/product/ForOnlineServices/all)
- **アクセス日**: 2026-07-04
- **原文引用（Competitive Benchmarking条項）**:
  > "If Customer offers a product or service competitive to an Online Service, by using the Online Service, Customer waives any restrictions on competitive use and benchmark testing in the terms governing its competitive products and services. If Customer offers a product or service competitive to an Online Service and discloses, directly or through third parties, any benchmarks or comparative tests or evaluations (each, a "Benchmark") of any Online Service, Customer will, upon request from Microsoft, provide: (a) all information necessary to replicate such Benchmark; and (b) access to Customer's competitive products and services for Microsoft, directly or through third parties, to perform and disclose Benchmarks."
- **判定**: ⚠️ 条件付き公開可
- **根拠**: 事前同意は不要。ただし、koedeskが「Azure AI Speechと競合する製品・サービス」を提供していると解釈された場合、ベンチマーク結果を公開すると、Microsoftから要求があれば(a)再現に必要な全情報の提供、(b)Microsoftによる（またはMicrosoftを通じた第三者による）koedeskへの反対ベンチマーク実施・公開への協力、が義務付けられる。koedeskは音声入力アプリであり音声認識プラットフォーム自体の提供者ではないため「競合製品」に該当するか自体グレー。この解釈の当否は❓要追加確認（法務判断が必要）。
- **注**: このドキュメントはAzure全体を含む汎用のOnline Services利用条件（Microsoft Customer Agreement配下）であり、Azure AI Speech固有の追加制限（Limited Access機能等）は今回未調査（STT自体はLimited Access対象外、TTSの音声クローン機能等が主にLimited Access対象）。

### 2.10 Speechmatics（候補）
- **文書**: [Terms of Service](https://www.speechmatics.com/legal/terms-of-service)
- **アクセス日**: 2026-07-04
- **調査結果**: 章立てはFees/Units/Hours等の定義を含む商用契約形式。ベンチマーク・性能比較・競合分析・公表禁止に関する条項は不在。
- **参考（規約ではない）**: Speechmatics自身が公式ブログで["How to accurately benchmark speech technology providers"](https://www.speechmatics.com/company/articles-and-news/how-to-accurately-benchmark-speech-technology-providers)という記事を公開しており、比較ベンチマーク文化そのものには前向きと推測される（ただしこれは規約ではなくマーケティング記事であり法的拘束力なし＝参考情報にとどめる）。
- **判定**: ✅ 公開可（要再確認）
- **根拠**: ToS本文に該当条項なし。ただし個別契約（Order Form等）で追加条項が入る可能性は他社同様に否定できない。

### 2.11 MAI-Transcribe-1.5（Microsoft・2026-07-05 追加監査）
- **文書**: [Microsoft Product Terms — Universal License Terms for Online Services](https://www.microsoft.com/licensing/terms/product/ForOnlineServices/all)、[Code of Conduct for Microsoft AI Services（v4.0, 2026-05-01）](https://learn.microsoft.com/en-us/legal/ai-code-of-conduct)、[Supplemental Terms of Use for Microsoft Azure Previews（June 2026）](https://azure.microsoft.com/en-us/support/legal/preview-supplemental-terms)、[MAI-Transcribe in LLM Speech API（Learn, 2026-05-28）](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/mai-transcribe)、[Foundry Models sold directly by Azure](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure)
- **アクセス日**: 2026-07-05
- **モデルの素性**: Microsoft AI (MAI) Superintelligence team 開発の **Microsoft first-party** モデル（2026-06-02 GA 発表・43言語・$0.36/h〜）。Foundry 上の区分は「Models sold directly by Azure」＝ Microsoft Product Terms が適用され、「Models from partners and community」向けのプロバイダ独自規約は**適用されない**。
- **適用条項**: §2.9 と同一の「Competitive Benchmarking」条項のみ（原文は §2.9 に引用済み）。Product Terms 変更履歴（最新公開 2026-07-01）の過去12ヶ月に同条項への変更なし＝現行有効を確認。ページ全文で "benchmark" の出現はこの条項のみで、旧来の「公表に事前書面承諾が必要」型条項は現行 Online Services 規約には存在しない。
- **Code of Conduct for Microsoft AI Services**: Responsible AI requirements / Usage restrictions（21項目）/ Content requirements のいずれにもベンチマーク・評価・比較公表の制限なし。
- **Generative AI Services 固有制限**: 禁止対象は①モデル内部構造の探索・重み抽出、②スクレイピングによるデータ抽出、③競合AIシステム訓練用の合成データ生成のみ。転写出力を正解と突合して WER/CER を計測・公表する行為はいずれにも非該当。"Output Content is Customer Data. Microsoft does not own Customer's Output Content." により生レスポンス全量保存・公開（R-2.5）も出力の権利面で問題なし。
- **Preview 規約**: 実 API（`speechtotext/transcriptions:transcribe?api-version=2025-10-15` + `enhancedMode.model: "mai-transcribe-1.5"`）は **public preview**（SLAなし）。Preview 補足規約にベンチマーク・性能公表の制限なし（守秘義務は限定 Early Access Preview のみに掛かる規定で public preview には非適用）。
- **判定**: ⚠️ 条件付き公開可（§2.9 と同条件）
- **根拠**: xAI 条項(j)型の禁止・事前承諾要件は不在。条件は §2.9 と同じ相互主義のみ＝(a) 再現情報の提供（公開 repo の設計で構造的に充足済み）(b) Microsoft による koedesk への反対ベンチマークの許容。
- **公平性上の注記（規約ではなく報告義務）**: preview API 経由での計測であることを結果公表時に明記する（GA 前の品質である可能性の開示）。
- **実測前の再確認事項**: ①Product Terms はサイト表示＝現行の建付けで版数スタンプがないため、実測開始時に条項スナップショット（日付入り）を本ファイルに残す ②Competitive Benchmarking 条項の放棄効果（koedesk 自身の利用規約に anti-benchmark 条項があれば Azure 利用により放棄したことになる）→ koedesk ToS の該当条項有無を確認 ③ベンチ対象12言語が MAI の対応43言語に全て含まれるか確認（含まれない言語は「非対応」表記＝設計上の論点）。

---

## 3. テストセットの再配布ライセンス

### 3.1 FLEURS（google/fleurs）
- **文書**: [HuggingFace Datasets API — google/fleurs](https://huggingface.co/api/datasets/google/fleurs)
- **アクセス日**: 2026-07-04
- **ライセンス**: `license:cc-by-4.0`（データセットのcardData/tagsに明記、CC BY 4.0 = Creative Commons Attribution 4.0 International）
- **再配布可否**: ✅ 可能。CC BY 4.0は商用・非商用問わず共有・改変・再頒布を許可する寛容なライセンス。**唯一の要件は適切なクレジット表記（Google/FLEURSへの帰属表示とライセンスへのリンク）**。
- **判定**: ✅ 音源そのものを公開リポジトリにコミットしても法的には問題ない（CC BY 4.0の要求＝出典表示を満たす限り）。ただし実務上は「取得スクリプト＋クレジット表記」の形にとどめる方が、リポジトリの肥大化回避・将来のデータセット更新追従の観点で望ましい（法務上の制約ではなく運用上の判断）。

### 3.2 Common Voice（Mozilla）
- **文書**: [Mozilla Data Collective Terms of Use](https://mozilladatacollective.com/terms)、各データセットページ（例: [Common Voice Scripted Speech 25.0 - Portuguese](https://mozilladatacollective.com/datasets/cmn29f4cb017bmm07pd9yd8mw)、[Common Voice Scripted Speech 26.0 - Japanese](https://mozilladatacollective.com/datasets/cmqim4lxy00tunr07cjkcupeg)）
- **アクセス日**: 2026-07-04
- **ライセンス（データセット自体）**: 従来通りCC0-1.0（Public Domain）表記が維持されている（2025年10月のMozilla Data Collectiveへの独占配信移行後も変更なしとの一次確認）。
- **⚠️重要な緊張関係**: データセット自体はCC0表記だが、**配信プラットフォームであるMozilla Data Collectiveの利用規約（Terms of Use）は、プラットフォーム外への再配布・ミラーリングを明示的に禁止する条項を持つ**。
- **原文引用（Mozilla Data Collective ToU）**:
  - Section 2.b(vii): "access, copy, download or use a Dataset outside the scope of your Data Consumer License"
  - Section 2.b(ix): "for the purpose of (A) mirroring, duplicating or reproducing the Dataset in whole or in substantial part, or (B) hosting, storing or making the Dataset available on any platform, server or repository other than the Platform, except as expressly permitted under the applicable Data Consumer License"
  - Section 2.b(x): 自動クローラー等によるプラットフォーム外への再配布目的の系統的取得を禁止
  - Section 3.c: "All rights in the Dataset remain exclusively with the applicable Data Provider"（CC0が個別のData Consumer Licenseとしてどう位置づけられるかは条文上明記されていない）
- **判定**: ⚠️ 条件付き（音源そのものの公開リポジトリへのコミットは非推奨）
- **根拠**: 「Data Consumer License」がCC0そのものであれば上記の禁止条項の適用除外（"except as expressly permitted under the applicable Data Consumer License"）に該当し再配布可能とも読めるが、CC0表記とプラットフォームToUの禁止条項がどちらが優先するかは今回の一次資料だけでは断定できない（❓要追加確認）。**安全側に倒すなら「取得スクリプト（Mozilla Data Collectiveから都度ダウンロードするコード）を公開リポジトリに置く」形にとどめ、音源ファイル自体を別リポジトリにコミット・再配布することは避けるべき**。

---

## 4. 未確認事項リスト（❓要追加確認）

1. **Gemini APIとGCP Service Specific Termsの関係**: Gemini API Additional ToS単体にはベンチマーク条項がないが、Gemini APIの基盤インフラ利用がGCPのService Specific Terms（第7条Benchmarking）の適用範囲に含まれるか否かは条文上明示されていない。Google側に問い合わせるか、Gemini API利用規約の親文書（Google Terms of Service本体）まで遡って確認が必要。
2. **Common Voice / Mozilla Data Collectiveの「Data Consumer License」の実体**: 個別データセットページで表示される「Data Consumer License」の全文（CC0がそのまま適用されるのか、プラットフォーム固有の追加制限が上乗せされるのか）を、実際にダウンロード手続きに進んで確認する必要がある（今回はデータセット一覧ページ止まりで、ダウンロード同意画面までは未到達）。
3. **Deepgram・Speechmatics・AmiVoiceの実際の契約書（Order Form／個別契約）**: 今回確認したのは公開されている標準ToS/PDFのみ。koedeskが実際に契約する際のOrder Formや個別条項（Enterprise契約等）に別途ベンチマーク制限が追加される可能性は排除できない。契約締結時に再確認が必要。
4. **Deepgram PDF2本の完全性**: `Business_TOS.pdf` と `DeepgramTermsofUse6717.pdf` はAI要約経由の読み取りであり、スキャン・圧縮に起因する読み落としの可能性を否定できない。人間による目視確認を推奨。
5. **Azure AI Speechが「競合製品」条項の対象になるか**: koedeskのようなエンドユーザー向け音声入力アプリが、Azure AI Speechという音声認識プラットフォームの「competitive product or service」に該当するかは解釈の余地がある。法務判断が必要。
6. **AssemblyAIからの個別許諾取得可能性**: AssemblyAIの禁止条項（2.4(f)）は絶対的な禁止であり、これを回避する唯一の手段は事前に書面での許諾を得ることだが、その許諾取得の実現可能性・手続きは今回未調査（AssemblyAIへの直接問い合わせが必要）。
7. **各社ToSの改定頻度**: 本調査はすべて2026-07-04時点のスナップショット。実際にベンチマークを実施・公開するタイミングで再度差分確認が望ましい（特にAI企業各社はToS改定が頻繁）。
