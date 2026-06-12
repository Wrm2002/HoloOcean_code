// MIT License (c) 2021 BYU FRoStLab see LICENSE file

#include "RaycastImagingSonar.h"

#include "DrawDebugHelpers.h"
#include "Holodeck.h"
#include "Json.h"
#include "Kismet/KismetMathLibrary.h"

URaycastImagingSonar::URaycastImagingSonar() {
	SensorName = "RaycastImagingSonar";
}

void URaycastImagingSonar::ParseSensorParms(FString ParmsJson) {
	Super::ParseSensorParms(ParmsJson);

	TSharedPtr<FJsonObject>		   JsonParsed;
	TSharedRef<TJsonReader<TCHAR>> JsonReader =
		TJsonReaderFactory<TCHAR>::Create(ParmsJson);

	if (!FJsonSerializer::Deserialize(JsonReader, JsonParsed) || !JsonParsed.IsValid()) {
		UE_LOG(
			LogHolodeck,
			Warning,
			TEXT("URaycastImagingSonar::ParseSensorParms: using default parameters."));
		return;
	}

	double NumberValue = 0.0;
	bool   BoolValue = false;

	if (JsonParsed->TryGetNumberField("RangeMin", NumberValue))
		RangeMin = NumberValue * 100.0f;
	if (JsonParsed->TryGetNumberField("RangeMax", NumberValue))
		RangeMax = NumberValue * 100.0f;
	if (JsonParsed->TryGetNumberField("Azimuth", NumberValue))
		Azimuth = NumberValue;
	if (JsonParsed->TryGetNumberField("Elevation", NumberValue))
		Elevation = NumberValue;
	if (JsonParsed->TryGetNumberField("RangeBins", NumberValue))
		RangeBins = FMath::Max(1, static_cast<int32>(NumberValue));
	if (JsonParsed->TryGetNumberField("AzimuthBins", NumberValue))
		AzimuthBins = FMath::Max(1, static_cast<int32>(NumberValue));
	if (JsonParsed->TryGetNumberField("ElevationSamples", NumberValue))
		ElevationSamples = FMath::Max(1, static_cast<int32>(NumberValue));
	if (JsonParsed->TryGetNumberField("TicksPerCapture", NumberValue))
		TicksPerCapture = FMath::Max(1, static_cast<int32>(NumberValue));
	if (JsonParsed->TryGetNumberField("Reflectivity", NumberValue))
		Reflectivity = NumberValue;
	if (JsonParsed->TryGetNumberField("BackgroundNoise", NumberValue))
		BackgroundNoise = FMath::Max(0.0f, static_cast<float>(NumberValue));
	if (JsonParsed->TryGetNumberField("IntensityScale", NumberValue))
		IntensityScale = NumberValue;
	if (JsonParsed->TryGetNumberField("IntensityRangePower", NumberValue))
		IntensityRangePower = FMath::Max(0.0f, static_cast<float>(NumberValue));
	if (JsonParsed->TryGetNumberField("RangeBias", NumberValue))
		RangeBias = NumberValue * 100.0f;
	if (JsonParsed->TryGetNumberField("RangeSpreadBins", NumberValue))
		RangeSpreadBins = FMath::Max(0, static_cast<int32>(NumberValue));
	if (JsonParsed->TryGetNumberField("AzimuthSpreadBins", NumberValue))
		AzimuthSpreadBins = FMath::Max(0, static_cast<int32>(NumberValue));
	if (JsonParsed->TryGetNumberField("RangeSpread", NumberValue))
		RangeSpread = FMath::Max(0.0f, static_cast<float>(NumberValue) * 100.0f);
	if (JsonParsed->TryGetNumberField("AzimuthSpread", NumberValue))
		AzimuthSpread = FMath::Max(0.0f, static_cast<float>(NumberValue));
	if (JsonParsed->TryGetBoolField("ShowDebug", BoolValue))
		ShowDebug = BoolValue;
	if (JsonParsed->TryGetBoolField("TraceComplex", BoolValue))
		TraceComplex = BoolValue;
}

void URaycastImagingSonar::InitializeSensor() {
	Super::InitializeSensor();

	Parent = this->GetAttachmentRootActor();
	ResultBuffer = static_cast<float*>(Buffer);
}

void URaycastImagingSonar::TickSensorComponent(
	float						 DeltaTime,
	ELevelTick					 TickType,
	FActorComponentTickFunction* ThisTickFunction) {
	TickCounter++;
	if (TickCounter >= TicksPerCapture) {
		SimulateSonar(DeltaTime);
		TickCounter = 0;
	}
}

void URaycastImagingSonar::SimulateSonar(float DeltaTime) {
	if (ResultBuffer == nullptr || GetWorld() == nullptr) {
		return;
	}

	const int32 NumPixels = RangeBins * AzimuthBins;
	for (int32 i = 0; i < NumPixels; ++i) {
		ResultBuffer[i] = BackgroundNoise > 0.0f ? FMath::FRand() * BackgroundNoise : 0.0f;
	}

	const FTransform SensorTransform = this->GetComponentTransform();
	const FVector	 Start = SensorTransform.GetLocation();
	const FRotator	 SensorRotation = SensorTransform.Rotator();
	const float		 AzimuthStep = AzimuthBins == 1 ? 0.0f : Azimuth / AzimuthBins;
	const float		 ElevationStep =
		ElevationSamples == 1 ? 0.0f : Elevation / (ElevationSamples - 1);

	FCollisionQueryParams TraceParams =
		FCollisionQueryParams(FName(TEXT("RaycastImagingSonar_Trace")), true, Parent);
	TraceParams.bTraceComplex = TraceComplex;
	TraceParams.bReturnPhysicalMaterial = true;

	for (int32 AzIdx = 0; AzIdx < AzimuthBins; ++AzIdx) {
		const float Yaw = -Azimuth / 2.0f + AzimuthStep * (AzIdx + 0.5f);

		for (int32 ElIdx = 0; ElIdx < ElevationSamples; ++ElIdx) {
			const float Pitch =
				ElevationSamples == 1 ? 0.0f
									  : -Elevation / 2.0f + ElevationStep * ElIdx;
			const FRotator BeamRotation =
				UKismetMathLibrary::ComposeRotators(FRotator(Pitch, Yaw, 0), SensorRotation);
			const FVector Direction = UKismetMathLibrary::GetForwardVector(BeamRotation);

			FHitResult HitResult(ForceInit);
			if (TraceBeam(Start, Direction, HitResult, TraceParams)) {
				AddHitToBuffer(HitResult, Direction);

				if (ShowDebug) {
					DrawDebugPoint(
						GetWorld(),
						HitResult.ImpactPoint,
						5.0f,
						FColor::Cyan,
						false,
						DeltaTime * TicksPerCapture);
				}
			}
		}
	}
}

bool URaycastImagingSonar::TraceBeam(
	const FVector&		   Start,
	const FVector&		   Direction,
	FHitResult&			   HitResult,
	FCollisionQueryParams& TraceParams) const {
	const FVector End = Start + Direction * RangeMax;

	GetWorld()->LineTraceSingleByChannel(
		HitResult,
		Start,
		End,
		ECC_Visibility,
		TraceParams,
		FCollisionResponseParams::DefaultResponseParam);

	if (!HitResult.bBlockingHit) {
		return false;
	}

	const float Distance = HitResult.Distance;
	return RangeMin <= Distance && Distance <= RangeMax;
}

void URaycastImagingSonar::AddHitToBuffer(
	const FHitResult& HitResult,
	const FVector&	 RayDirection) {
	const float RangeSpan = FMath::Max(1.0f, RangeMax - RangeMin);
	const float BiasedDistance =
		FMath::Clamp(HitResult.Distance + RangeBias, RangeMin, RangeMax);
	const float RangeBin =
		FMath::Clamp(
			(BiasedDistance - RangeMin) / RangeSpan * RangeBins,
			0.0f,
			RangeBins - 1.0f);

	const FTransform SensorTransform = this->GetComponentTransform();
	const FVector	 LocalHit =
		SensorTransform.GetRotation().UnrotateVector(
			HitResult.ImpactPoint - SensorTransform.GetLocation());
	const float AzimuthDeg = UKismetMathLibrary::DegAtan2(-LocalHit.Y, LocalHit.X);
	const float AzimuthBin =
		FMath::Clamp(
			(AzimuthDeg + Azimuth / 2.0f) / Azimuth * AzimuthBins,
			0.0f,
			AzimuthBins - 1.0f);

	const float NormalTerm =
		FMath::Clamp(FVector::DotProduct(HitResult.ImpactNormal, -RayDirection), 0.0f, 1.0f);
	const float RangeMeters = FMath::Max(BiasedDistance / 100.0f, 0.1f);
	const float RangeDenominator =
		IntensityRangePower <= 0.0f ? 1.0f : FMath::Pow(RangeMeters, IntensityRangePower);
	const float Intensity =
		IntensityScale * Reflectivity * NormalTerm / FMath::Max(RangeDenominator, 0.01f);

	AccumulateHit(RangeBin, AzimuthBin, Intensity);
}

void URaycastImagingSonar::AccumulateHit(
	float RangeBin,
	float AzimuthBin,
	float Intensity) {
	const int32 CenterRange = FMath::Clamp(FMath::RoundToInt(RangeBin), 0, RangeBins - 1);
	const int32 CenterAzimuth =
		FMath::Clamp(FMath::RoundToInt(AzimuthBin), 0, AzimuthBins - 1);
	const float RangeSpan = FMath::Max(1.0f, RangeMax - RangeMin);
	const int32 EffectiveRangeSpreadBins =
		RangeSpread > 0.0f
			? FMath::Max(0, FMath::CeilToInt(RangeSpread / RangeSpan * RangeBins))
			: RangeSpreadBins;
	const int32 EffectiveAzimuthSpreadBins =
		AzimuthSpread > 0.0f
			? FMath::Max(0, FMath::CeilToInt(AzimuthSpread / Azimuth * AzimuthBins))
			: AzimuthSpreadBins;

	if (EffectiveRangeSpreadBins == 0 && EffectiveAzimuthSpreadBins == 0) {
		const int32 BufferIdx = CenterRange * AzimuthBins + CenterAzimuth;
		ResultBuffer[BufferIdx] += Intensity;
		return;
	}

	const int32 MinRange = FMath::Max(0, CenterRange - EffectiveRangeSpreadBins);
	const int32 MaxRange = FMath::Min(RangeBins - 1, CenterRange + EffectiveRangeSpreadBins);
	const int32 MinAzimuth = FMath::Max(0, CenterAzimuth - EffectiveAzimuthSpreadBins);
	const int32 MaxAzimuth = FMath::Min(AzimuthBins - 1, CenterAzimuth + EffectiveAzimuthSpreadBins);
	const float RangeSigma =
		FMath::Max(static_cast<float>(EffectiveRangeSpreadBins) * 0.5f, 0.5f);
	const float AzimuthSigma =
		FMath::Max(static_cast<float>(EffectiveAzimuthSpreadBins) * 0.5f, 0.5f);

	float WeightSum = 0.0f;
	for (int32 RangeIdx = MinRange; RangeIdx <= MaxRange; ++RangeIdx) {
		const float RangeDelta = (static_cast<float>(RangeIdx) - RangeBin) / RangeSigma;
		for (int32 AzimuthIdx = MinAzimuth; AzimuthIdx <= MaxAzimuth; ++AzimuthIdx) {
			const float AzimuthDelta =
				(static_cast<float>(AzimuthIdx) - AzimuthBin) / AzimuthSigma;
			WeightSum += FMath::Exp(
				-0.5f * (RangeDelta * RangeDelta + AzimuthDelta * AzimuthDelta));
		}
	}

	if (WeightSum <= 0.0f) {
		return;
	}

	const float NormalizedIntensity = Intensity / WeightSum;
	for (int32 RangeIdx = MinRange; RangeIdx <= MaxRange; ++RangeIdx) {
		const float RangeDelta = (static_cast<float>(RangeIdx) - RangeBin) / RangeSigma;
		for (int32 AzimuthIdx = MinAzimuth; AzimuthIdx <= MaxAzimuth; ++AzimuthIdx) {
			const float AzimuthDelta =
				(static_cast<float>(AzimuthIdx) - AzimuthBin) / AzimuthSigma;
			const float Weight =
				FMath::Exp(-0.5f * (RangeDelta * RangeDelta + AzimuthDelta * AzimuthDelta));
			const int32 BufferIdx = RangeIdx * AzimuthBins + AzimuthIdx;
			ResultBuffer[BufferIdx] += NormalizedIntensity * Weight;
		}
	}
}
