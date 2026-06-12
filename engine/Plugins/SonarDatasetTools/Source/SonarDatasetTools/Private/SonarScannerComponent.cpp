#include "SonarScannerComponent.h"
#include "Dom/JsonObject.h"
#include "DrawDebugHelpers.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "IImageWrapper.h"
#include "IImageWrapperModule.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Modules/ModuleManager.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "TextureResource.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/Scene.h"
#include "Engine/TextureRenderTarget2D.h"

namespace
{
bool TryReadClassIdFromActorTags(const AActor* Actor, int32& OutClassId)
{
	if (!IsValid(Actor))
	{
		return false;
	}

	for (const FName& TagName : Actor->Tags)
	{
		FString Tag = TagName.ToString().ToLower();
		Tag.TrimStartAndEndInline();

		FString Value;
		if (Tag.Split(TEXT("class_"), nullptr, &Value) ||
			Tag.Split(TEXT("class="), nullptr, &Value) ||
			Tag.Split(TEXT("class:"), nullptr, &Value) ||
			Tag.Split(TEXT("yolo_"), nullptr, &Value) ||
			Tag.Split(TEXT("yolo="), nullptr, &Value) ||
			Tag.Split(TEXT("yolo:"), nullptr, &Value))
		{
			if (!Value.IsEmpty() && Value.IsNumeric())
			{
				OutClassId = FCString::Atoi(*Value);
				return true;
			}
		}
	}

	return false;
}

bool IsActorMarkedForSonarLabel(const AActor* Actor)
{
	if (!IsValid(Actor))
	{
		return false;
	}

	for (const FName& TagName : Actor->Tags)
	{
		FString Tag = TagName.ToString().ToLower();
		Tag.TrimStartAndEndInline();

		if (Tag == TEXT("sonar_target") || Tag == TEXT("sonartarget") || Tag == TEXT("target"))
		{
			return true;
		}
	}

	int32 IgnoredClassId = INDEX_NONE;
	return TryReadClassIdFromActorTags(Actor, IgnoredClassId);
}

float GetMaterialReflectivityMultiplier(
	const AActor* Actor,
	float RockReflectivity,
	float MetalReflectivity,
	float SandReflectivity,
	float PlantReflectivity)
{
	if (!IsValid(Actor))
	{
		return 1.0f;
	}

	for (const FName& TagName : Actor->Tags)
	{
		FString Tag = TagName.ToString().ToLower();
		Tag.TrimStartAndEndInline();

		if (Tag == TEXT("material_rock") || Tag == TEXT("acoustic_rock"))
		{
			return RockReflectivity;
		}
		if (Tag == TEXT("material_metal") || Tag == TEXT("acoustic_metal"))
		{
			return MetalReflectivity;
		}
		if (Tag == TEXT("material_sand") || Tag == TEXT("acoustic_sand"))
		{
			return SandReflectivity;
		}
		if (Tag == TEXT("material_plant") || Tag == TEXT("acoustic_plant") || Tag == TEXT("material_vegetation"))
		{
			return PlantReflectivity;
		}
	}

	return 1.0f;
}

FString EscapeCsvField(const FString& Value)
{
	FString Escaped = Value;
	Escaped.ReplaceInline(TEXT("\""), TEXT("\"\""));
	if (Escaped.Contains(TEXT(",")) || Escaped.Contains(TEXT("\"")) || Escaped.Contains(TEXT("\n")) || Escaped.Contains(TEXT("\r")))
	{
		return TEXT("\"") + Escaped + TEXT("\"");
	}
	return Escaped;
}
}

USonarScannerComponent::USonarScannerComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
}

void USonarScannerComponent::BeginPlay()
{
	Super::BeginPlay();
	SetupAutoRgbCapture();
}

void USonarScannerComponent::SetupAutoRgbCapture()
{
	if (!bAutoCreateRgbCapture || !IsValid(GetOwner()))
	{
		return;
	}

	if (!IsValid(RgbRenderTarget))
	{
		RgbRenderTarget = NewObject<UTextureRenderTarget2D>(this, TEXT("AutoRgbRenderTarget"));
		RgbRenderTarget->RenderTargetFormat = RTF_RGBA8;
		RgbRenderTarget->ClearColor = FLinearColor::Black;
		RgbRenderTarget->bAutoGenerateMips = false;
		RgbRenderTarget->InitAutoFormat(FMath::Max(16, RgbImageWidth), FMath::Max(16, RgbImageHeight));
		RgbRenderTarget->UpdateResourceImmediate(true);
	}

	if (!IsValid(AutoRgbCapture))
	{
		AActor* Owner = GetOwner();
		AutoRgbCapture = NewObject<USceneCaptureComponent2D>(Owner, TEXT("AutoRgbSceneCapture"));
		AutoRgbCapture->RegisterComponent();
		if (USceneComponent* Root = Owner->GetRootComponent())
		{
			AutoRgbCapture->AttachToComponent(Root, FAttachmentTransformRules::KeepRelativeTransform);
		}
	}

	AutoRgbCapture->SetRelativeLocation(RgbLocalOffset);
	AutoRgbCapture->SetRelativeRotation(FRotator::ZeroRotator);
	AutoRgbCapture->FOVAngle = RgbFovDegrees;
	AutoRgbCapture->TextureTarget = RgbRenderTarget;
	AutoRgbCapture->CaptureSource = SCS_FinalColorLDR;
	AutoRgbCapture->bCaptureEveryFrame = false;
	AutoRgbCapture->bCaptureOnMovement = false;
	AutoRgbCapture->ShowFlags.SetOnScreenDebug(false);
	AutoRgbCapture->ShowFlags.SetServerDrawDebug(false);

	if (bLockRgbExposure)
	{
		AutoRgbCapture->PostProcessBlendWeight = 1.0f;
		AutoRgbCapture->PostProcessSettings.bOverride_AutoExposureMethod = true;
		AutoRgbCapture->PostProcessSettings.AutoExposureMethod = AEM_Manual;
		AutoRgbCapture->PostProcessSettings.bOverride_AutoExposureBias = true;
		AutoRgbCapture->PostProcessSettings.AutoExposureBias = RgbExposureBias;
		AutoRgbCapture->PostProcessSettings.bOverride_AutoExposureApplyPhysicalCameraExposure = true;
		AutoRgbCapture->PostProcessSettings.AutoExposureApplyPhysicalCameraExposure = false;
	}
	else
	{
		AutoRgbCapture->PostProcessBlendWeight = 0.0f;
	}
}

void USonarScannerComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

	if (bScanEveryTick)
	{
		Scan();
	}

	if (bAutoSaveDatasetFrames && (MaxAutoSaveFrames <= 0 || AutoSavedFrameCount < MaxAutoSaveFrames))
	{
		AutoSaveAccumulatorSeconds += DeltaTime;
		if (AutoSaveAccumulatorSeconds >= AutoSaveIntervalSeconds)
		{
			AutoSaveAccumulatorSeconds = 0.0f;
			if (SaveDatasetFrame())
			{
				++AutoSavedFrameCount;
			}
		}
	}
}

void USonarScannerComponent::ClearScanData()
{
	WorldHitPoints.Reset();
	LocalHitPoints.Reset();
	SonarPixelPoints.Reset();
	HitActors.Reset();
	HitDistances.Reset();
	HitNormals.Reset();
	HitIntensities.Reset();
	YoloBoxes.Reset();
	YoloText.Reset();
	LastHitCount = 0;
}

void USonarScannerComponent::Scan()
{
	ClearScanData();

	AActor* Owner = GetOwner();
	UWorld* World = GetWorld();
	if (!IsValid(Owner) || !IsValid(World) || NumTraces <= 0 || TraceLength <= KINDA_SMALL_NUMBER)
	{
		return;
	}

	const FTransform OwnerTransform = Owner->GetActorTransform();
	const FVector Start = OwnerTransform.TransformPosition(LocalOriginOffset);
	const float CenterIndex = static_cast<float>(NumTraces - 1) * 0.5f;
	const int32 SafeVerticalSamples = FMath::Max(1, VerticalSamples);
	const float CenterVerticalIndex = static_cast<float>(SafeVerticalSamples - 1) * 0.5f;
	const int32 CenterVerticalDebugIndex = FMath::RoundToInt(CenterVerticalIndex);
	const float VerticalStepDegrees = SafeVerticalSamples > 1
		? VerticalFovDegrees / static_cast<float>(SafeVerticalSamples - 1)
		: 0.0f;

	auto ProjectLocalHitToSonarPixel = [this](const FVector& LocalPoint, float SlantRange)
	{
		const float BearingRadians = FMath::Atan2(LocalPoint.Y, LocalPoint.X);
		const float RangePixels = FMath::Clamp(SlantRange / FMath::Max(1.0f, TraceLength), 0.0f, 1.0f) * SonarDrawRadius;
		const FVector2D PixelPoint(
			SonarOriginX + FMath::Sin(BearingRadians) * RangePixels,
			SonarOriginY - FMath::Cos(BearingRadians) * RangePixels);

		if (!bClampPixelsToImage)
		{
			return PixelPoint;
		}

		return FVector2D(
			FMath::Clamp(PixelPoint.X, 0.0f, ImageWidth),
			FMath::Clamp(PixelPoint.Y, 0.0f, ImageHeight));
	};

	FCollisionQueryParams QueryParams(SCENE_QUERY_STAT(SonarScannerComponent), false, Owner);
	QueryParams.AddIgnoredActor(Owner);

	const int32 MaxRayCount = NumTraces * SafeVerticalSamples;
	WorldHitPoints.Reserve(MaxRayCount);
	LocalHitPoints.Reserve(MaxRayCount);
	SonarPixelPoints.Reserve(MaxRayCount);
	HitActors.Reserve(MaxRayCount);
	HitDistances.Reserve(MaxRayCount);
	HitNormals.Reserve(MaxRayCount);
	HitIntensities.Reserve(MaxRayCount);

	for (int32 Index = 0; Index < NumTraces; ++Index)
	{
		const float YawOffset = (static_cast<float>(Index) - CenterIndex) * DegreesPerTrace + CenterYawOffsetDegrees;
		for (int32 VerticalIndex = 0; VerticalIndex < SafeVerticalSamples; ++VerticalIndex)
		{
			const float PitchOffset = (static_cast<float>(VerticalIndex) - CenterVerticalIndex) * VerticalStepDegrees + CenterPitchOffsetDegrees;
			const FVector LocalDirection = FRotator(PitchOffset, YawOffset, 0.0f).RotateVector(FVector::ForwardVector).GetSafeNormal();
			const FVector Direction = OwnerTransform.TransformVectorNoScale(LocalDirection).GetSafeNormal();
			const FVector End = Start + Direction * TraceLength;

			FHitResult Hit;
			const bool bHit = World->LineTraceSingleByChannel(Hit, Start, End, TraceChannel, QueryParams);

			if (bDrawDebug && (bDrawAllVerticalDebugRays || VerticalIndex == CenterVerticalDebugIndex))
			{
				const FColor Color = bHit ? FColor::Red : FColor::Green;
				DrawDebugLine(World, Start, bHit ? Hit.ImpactPoint : End, Color, false, DebugLineDuration, 0, 1.0f);
			}

			if (!bHit)
			{
				continue;
			}

			const FVector WorldPoint = Hit.ImpactPoint;
			const FVector LocalPoint = OwnerTransform.InverseTransformPosition(WorldPoint);
			const FVector2D PixelPoint = ProjectLocalHitToSonarPixel(LocalPoint, Hit.Distance);

			WorldHitPoints.Add(WorldPoint);
			LocalHitPoints.Add(LocalPoint);
			SonarPixelPoints.Add(PixelPoint);
			HitActors.Add(Hit.GetActor());
			HitDistances.Add(Hit.Distance);
			HitNormals.Add(Hit.ImpactNormal);

			float Intensity = FMath::Clamp(-FVector::DotProduct(Direction, Hit.ImpactNormal.GetSafeNormal()), 0.0f, 1.0f);
			if (SafeVerticalSamples > 1)
			{
				const float VerticalAlpha = FMath::Abs(static_cast<float>(VerticalIndex) - CenterVerticalIndex) / CenterVerticalIndex;
				Intensity *= FMath::Lerp(1.0f, 0.62f, FMath::Clamp(VerticalAlpha, 0.0f, 1.0f));
			}
			if (bApplyDistanceFalloff)
			{
				const float DistanceAlpha = FMath::Clamp(Hit.Distance / TraceLength, 0.0f, 1.0f);
				Intensity *= 1.0f - 0.35f * DistanceAlpha;
			}
			if (bApplyMaterialReflectivity)
			{
				Intensity *= GetMaterialReflectivityMultiplier(
					Hit.GetActor(),
					RockReflectivity,
					MetalReflectivity,
					SandReflectivity,
					PlantReflectivity);
			}
			Intensity = FMath::Clamp(Intensity, 0.0f, 1.0f);
			HitIntensities.Add(Intensity);
		}
	}

	LastHitCount = WorldHitPoints.Num();

	if (bBuildYoloEveryScan)
	{
		TArray<AActor*> RawActors;
		RawActors.Reserve(HitActors.Num());
		for (AActor* Actor : HitActors)
		{
			RawActors.Add(!bOnlyLabelTaggedActors || IsActorMarkedForSonarLabel(Actor) ? Actor : nullptr);
		}

		USonarDatasetBlueprintLibrary::BuildYoloBoxesFromSonarPixels(
			SonarPixelPoints,
			RawActors,
			ImageWidth,
			ImageHeight,
			DefaultClassId,
			YoloBoxes,
			YoloText);
	}
}

FString USonarScannerComponent::GetFrameStem() const
{
	return FString::Printf(TEXT("%s%06d"), *FilePrefix, FrameIndex);
}

float USonarScannerComponent::GenerateGaussian(float StdDev) const
{
	if (StdDev <= 0.0f)
	{
		return 0.0f;
	}

	const float U1 = FMath::Max(FMath::FRand(), 0.000001f);
	const float U2 = FMath::FRand();
	const float Z0 = FMath::Sqrt(-2.0f * FMath::Loge(U1)) * FMath::Cos(2.0f * PI * U2);
	return Z0 * StdDev;
}

void USonarScannerComponent::GenerateSonarImage(TArray<FColor>& Pixels) const
{
	const int32 Width = FMath::Max(1, FMath::RoundToInt(ImageWidth));
	const int32 Height = FMath::Max(1, FMath::RoundToInt(ImageHeight));
	Pixels.SetNum(Width * Height);

	const float HalfFovDegrees = FMath::Abs(DegreesPerTrace) * static_cast<float>(FMath::Max(0, NumTraces - 1)) * 0.5f;
	const float MaxDrawRadius = FMath::Max(1.0f, SonarDrawRadius);

	for (int32 Y = 0; Y < Height; ++Y)
	{
		for (int32 X = 0; X < Width; ++X)
		{
			const float Dx = static_cast<float>(X) - SonarOriginX;
			const float Dy = SonarOriginY - static_cast<float>(Y);
			const float Radius = FMath::Sqrt(Dx * Dx + Dy * Dy);
			const float AngleDegrees = FMath::RadiansToDegrees(FMath::Atan2(Dx, Dy));
			const bool bInsideFan =
				Radius <= MaxDrawRadius &&
				FMath::Abs(FMath::FindDeltaAngleDegrees(CenterYawOffsetDegrees, AngleDegrees)) <= HalfFovDegrees;

			int32 Value = 0;
			if (bInsideFan && bDrawFanBackground)
			{
				Value = FanBackgroundValue;
				if (bUseGaussianNoise)
				{
					Value += FMath::RoundToInt(GenerateGaussian(BackgroundNoiseStdDev));
				}

				const float RangeFalloff = FMath::Clamp(Radius / MaxDrawRadius, 0.0f, 1.0f);
				Value = FMath::RoundToInt(static_cast<float>(Value) * (1.0f - 0.25f * RangeFalloff));

				if (bDrawRangeRings && RangeRingSpacingPixels > 0)
				{
					const float RingDistance = FMath::Abs(FMath::Fmod(Radius, static_cast<float>(RangeRingSpacingPixels)));
					if (RingDistance < 1.25f || RingDistance > static_cast<float>(RangeRingSpacingPixels) - 1.25f)
					{
						Value = FMath::Max(Value, RangeRingValue);
					}
				}
			}

			const uint8 ClampedValue = static_cast<uint8>(FMath::Clamp(Value, 0, 255));
			Pixels[Y * Width + X] = FColor(ClampedValue, ClampedValue, ClampedValue, 255);
		}
	}

	for (int32 Index = 0; Index < SonarPixelPoints.Num(); ++Index)
	{
		const FVector2D Pixel = SonarPixelPoints[Index];
		const float BaseIntensity = HitIntensities.IsValidIndex(Index) ? HitIntensities[Index] : 1.0f;
		const int32 CenterX = FMath::RoundToInt(Pixel.X);
		const int32 CenterY = FMath::RoundToInt(Pixel.Y);
		const int32 Radius = bUseRealisticEcho
			? FMath::CeilToInt(FMath::Max(EchoAngularSigmaPixels, EchoRangeSigmaPixels) * 3.0f)
			: FMath::Max(0, PingRadiusPixels);

		if (bUseRealisticEcho && bDrawAcousticShadow)
		{
			const float Dx = Pixel.X - SonarOriginX;
			const float Dy = SonarOriginY - Pixel.Y;
			const float HitRadius = FMath::Sqrt(Dx * Dx + Dy * Dy);
			if (HitRadius > KINDA_SMALL_NUMBER)
			{
				const FVector2D Direction(Dx / HitRadius, Dy / HitRadius);
				const int32 ShadowHalfWidth = FMath::Max(1, FMath::RoundToInt(EchoAngularSigmaPixels * 1.8f));
				const int32 MaxShadowStep = FMath::Min(ShadowLengthPixels, FMath::FloorToInt(MaxDrawRadius - HitRadius));
				for (int32 Step = 1; Step <= MaxShadowStep; ++Step)
				{
					const float ShadowRadius = HitRadius + static_cast<float>(Step);
					const int32 ShadowCenterX = FMath::RoundToInt(SonarOriginX + Direction.X * ShadowRadius);
					const int32 ShadowCenterY = FMath::RoundToInt(SonarOriginY - Direction.Y * ShadowRadius);
					const float RangeFade = 1.0f - static_cast<float>(Step) / static_cast<float>(MaxShadowStep + 1);
					const float ShadowAlpha = ShadowStrength * RangeFade;

					for (int32 Offset = -ShadowHalfWidth; Offset <= ShadowHalfWidth; ++Offset)
					{
						const int32 DrawX = ShadowCenterX + FMath::RoundToInt(-Direction.Y * static_cast<float>(Offset));
						const int32 DrawY = ShadowCenterY + FMath::RoundToInt(-Direction.X * static_cast<float>(Offset));
						if (DrawX < 0 || DrawX >= Width || DrawY < 0 || DrawY >= Height)
						{
							continue;
						}

						const float AcrossFade = FMath::Exp(-(static_cast<float>(Offset * Offset)) / (2.0f * EchoAngularSigmaPixels * EchoAngularSigmaPixels));
						const int32 Existing = Pixels[DrawY * Width + DrawX].R;
						const uint8 NewValue = static_cast<uint8>(FMath::Clamp(FMath::RoundToInt(static_cast<float>(Existing) * (1.0f - ShadowAlpha * AcrossFade)), 0, 255));
						Pixels[DrawY * Width + DrawX] = FColor(NewValue, NewValue, NewValue, 255);
					}
				}
			}
		}

		for (int32 OffsetY = -Radius; OffsetY <= Radius; ++OffsetY)
		{
			for (int32 OffsetX = -Radius; OffsetX <= Radius; ++OffsetX)
			{
				const int32 DrawX = CenterX + OffsetX;
				const int32 DrawY = CenterY + OffsetY;
				if (DrawX < 0 || DrawX >= Width || DrawY < 0 || DrawY >= Height)
				{
					continue;
				}

				float Falloff = 1.0f;
				if (bUseRealisticEcho)
				{
					const float Angular = static_cast<float>(OffsetX) / FMath::Max(0.1f, EchoAngularSigmaPixels);
					const float Range = static_cast<float>(OffsetY) / FMath::Max(0.1f, EchoRangeSigmaPixels);
					Falloff = FMath::Exp(-0.5f * (Angular * Angular + Range * Range));

					if (OffsetY > 0)
					{
						const float Tail = FMath::Exp(-static_cast<float>(OffsetY) / FMath::Max(1.0f, EchoRangeSigmaPixels * 2.2f));
						Falloff = FMath::Max(Falloff, EchoTailStrength * Tail * FMath::Exp(-0.5f * Angular * Angular));
					}

					if (Falloff < 0.015f)
					{
						continue;
					}
				}
				else
				{
					const float DistanceFromCenter = FVector2D(OffsetX, OffsetY).Length();
					if (DistanceFromCenter > static_cast<float>(Radius) + 0.01f)
					{
						continue;
					}
					Falloff = Radius > 0 ? 1.0f - DistanceFromCenter / static_cast<float>(Radius + 1) : 1.0f;
				}

				const int32 Existing = Pixels[DrawY * Width + DrawX].R;
				const int32 Added = FMath::RoundToInt(BaseIntensity * IntensityScale * Falloff + GenerateGaussian(PingNoiseStdDev));
				const uint8 NewValue = static_cast<uint8>(FMath::Clamp(FMath::Max(Existing, Added), 0, 255));
				Pixels[DrawY * Width + DrawX] = FColor(NewValue, NewValue, NewValue, 255);
			}
		}
	}
}

bool USonarScannerComponent::SavePngFile(const FString& AbsolutePath, const TArray<FColor>& Pixels, int32 Width, int32 Height) const
{
	if (Pixels.Num() != Width * Height)
	{
		return false;
	}

	IImageWrapperModule& ImageWrapperModule = FModuleManager::LoadModuleChecked<IImageWrapperModule>(TEXT("ImageWrapper"));
	const TSharedPtr<IImageWrapper> ImageWrapper = ImageWrapperModule.CreateImageWrapper(EImageFormat::PNG);
	if (!ImageWrapper.IsValid())
	{
		return false;
	}

	if (!ImageWrapper->SetRaw(Pixels.GetData(), Pixels.Num() * sizeof(FColor), Width, Height, ERGBFormat::BGRA, 8))
	{
		return false;
	}

	const TArray64<uint8>& Compressed = ImageWrapper->GetCompressed(100);
	TArray<uint8> Bytes;
	Bytes.Append(Compressed.GetData(), Compressed.Num());
	return FFileHelper::SaveArrayToFile(Bytes, *AbsolutePath);
}

bool USonarScannerComponent::SaveRgbRenderTarget(const FString& AbsolutePath) const
{
	if (!IsValid(RgbRenderTarget))
	{
		return false;
	}

	if (IsValid(AutoRgbCapture))
	{
		AutoRgbCapture->CaptureScene();
	}

	FTextureRenderTargetResource* Resource = RgbRenderTarget->GameThread_GetRenderTargetResource();
	if (!Resource)
	{
		return false;
	}

	TArray<FColor> Pixels;
	FReadSurfaceDataFlags ReadFlags(RCM_UNorm);
	ReadFlags.SetLinearToGamma(true);
	if (!Resource->ReadPixels(Pixels, ReadFlags))
	{
		return false;
	}

	return SavePngFile(AbsolutePath, Pixels, RgbRenderTarget->SizeX, RgbRenderTarget->SizeY);
}

bool USonarScannerComponent::SavePointCloudCsvFile(const FString& AbsolutePath) const
{
	FString CsvText;
	CsvText.Reserve(WorldHitPoints.Num() * 180);
	CsvText += TEXT("point_index,world_x_m,world_y_m,world_z_m,local_x_m,local_y_m,local_z_m,range_m,azimuth_deg,elevation_deg,intensity,normal_x,normal_y,normal_z,sonar_px,sonar_py,actor_name,class_id\n");

	constexpr float CmToM = 0.01f;
	for (int32 Index = 0; Index < WorldHitPoints.Num(); ++Index)
	{
		const FVector WorldPoint = WorldHitPoints[Index];
		const FVector LocalPoint = LocalHitPoints.IsValidIndex(Index) ? LocalHitPoints[Index] : FVector::ZeroVector;
		const FVector Normal = HitNormals.IsValidIndex(Index) ? HitNormals[Index] : FVector::ZeroVector;
		const FVector2D SonarPixel = SonarPixelPoints.IsValidIndex(Index) ? SonarPixelPoints[Index] : FVector2D::ZeroVector;
		const float RangeCm = HitDistances.IsValidIndex(Index) ? HitDistances[Index] : LocalPoint.Length();
		const float Intensity = HitIntensities.IsValidIndex(Index) ? HitIntensities[Index] : 0.0f;
		const float HorizontalRange = FMath::Sqrt(LocalPoint.X * LocalPoint.X + LocalPoint.Y * LocalPoint.Y);
		const float AzimuthDeg = FMath::RadiansToDegrees(FMath::Atan2(LocalPoint.Y, LocalPoint.X));
		const float ElevationDeg = FMath::RadiansToDegrees(FMath::Atan2(LocalPoint.Z, HorizontalRange));

		const AActor* HitActor = HitActors.IsValidIndex(Index) ? HitActors[Index].Get() : nullptr;
		int32 ClassId = INDEX_NONE;
		if (IsActorMarkedForSonarLabel(HitActor) && !TryReadClassIdFromActorTags(HitActor, ClassId))
		{
			ClassId = DefaultClassId;
		}
		const FString ActorName = IsValid(HitActor) ? HitActor->GetName() : FString();

		CsvText += FString::Printf(
			TEXT("%d,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.4f,%.4f,%.6f,%.6f,%.6f,%.6f,%.3f,%.3f,%s,%d\n"),
			Index,
			WorldPoint.X * CmToM,
			WorldPoint.Y * CmToM,
			WorldPoint.Z * CmToM,
			LocalPoint.X * CmToM,
			LocalPoint.Y * CmToM,
			LocalPoint.Z * CmToM,
			RangeCm * CmToM,
			AzimuthDeg,
			ElevationDeg,
			Intensity,
			Normal.X,
			Normal.Y,
			Normal.Z,
			SonarPixel.X,
			SonarPixel.Y,
			*EscapeCsvField(ActorName),
			ClassId);
	}

	return FFileHelper::SaveStringToFile(CsvText, *AbsolutePath);
}

bool USonarScannerComponent::SavePointCloudPlyFile(const FString& AbsolutePath) const
{
	FString PlyText;
	PlyText.Reserve(WorldHitPoints.Num() * 96);
	PlyText += TEXT("ply\n");
	PlyText += TEXT("format ascii 1.0\n");
	PlyText += TEXT("comment generated_by SonarDatasetTools\n");
	PlyText += TEXT("comment unit meter\n");
	PlyText += FString::Printf(TEXT("element vertex %d\n"), WorldHitPoints.Num());
	PlyText += TEXT("property float x\n");
	PlyText += TEXT("property float y\n");
	PlyText += TEXT("property float z\n");
	PlyText += TEXT("property float intensity\n");
	PlyText += TEXT("property float range\n");
	PlyText += TEXT("property float azimuth\n");
	PlyText += TEXT("property float elevation\n");
	PlyText += TEXT("property int class_id\n");
	PlyText += TEXT("end_header\n");

	constexpr float CmToM = 0.01f;
	for (int32 Index = 0; Index < WorldHitPoints.Num(); ++Index)
	{
		const FVector WorldPoint = WorldHitPoints[Index];
		const FVector LocalPoint = LocalHitPoints.IsValidIndex(Index) ? LocalHitPoints[Index] : FVector::ZeroVector;
		const float RangeCm = HitDistances.IsValidIndex(Index) ? HitDistances[Index] : LocalPoint.Length();
		const float Intensity = HitIntensities.IsValidIndex(Index) ? HitIntensities[Index] : 0.0f;
		const float HorizontalRange = FMath::Sqrt(LocalPoint.X * LocalPoint.X + LocalPoint.Y * LocalPoint.Y);
		const float AzimuthDeg = FMath::RadiansToDegrees(FMath::Atan2(LocalPoint.Y, LocalPoint.X));
		const float ElevationDeg = FMath::RadiansToDegrees(FMath::Atan2(LocalPoint.Z, HorizontalRange));

		const AActor* HitActor = HitActors.IsValidIndex(Index) ? HitActors[Index].Get() : nullptr;
		int32 ClassId = INDEX_NONE;
		if (IsActorMarkedForSonarLabel(HitActor) && !TryReadClassIdFromActorTags(HitActor, ClassId))
		{
			ClassId = DefaultClassId;
		}

		PlyText += FString::Printf(
			TEXT("%.6f %.6f %.6f %.6f %.6f %.4f %.4f %d\n"),
			WorldPoint.X * CmToM,
			WorldPoint.Y * CmToM,
			WorldPoint.Z * CmToM,
			Intensity,
			RangeCm * CmToM,
			AzimuthDeg,
			ElevationDeg,
			ClassId);
	}

	return FFileHelper::SaveStringToFile(PlyText, *AbsolutePath);
}

bool USonarScannerComponent::AppendManifestRow(
	const FString& RootDir,
	const FString& Stem,
	const FString& SonarImagePath,
	const FString& LabelPath,
	const FString& MetaPath,
	const FString& RgbImagePath,
	const FString& PointCloudCsvPath,
	const FString& PointCloudPlyPath) const
{
	const FString CsvPath = RootDir / TEXT("dataset_index.csv");
	const bool bNeedsHeader = !IFileManager::Get().FileExists(*CsvPath);

	FString Row;
	if (bNeedsHeader)
	{
		Row += TEXT("frame,sonar_image,rgb_image,label_file,meta_file,point_cloud_csv,point_cloud_ply,hit_count,object_count\n");
	}

	Row += FString::Printf(
		TEXT("%s,%s,%s,%s,%s,%s,%s,%d,%d\n"),
		*Stem,
		*SonarImagePath,
		*RgbImagePath,
		*LabelPath,
		*MetaPath,
		*PointCloudCsvPath,
		*PointCloudPlyPath,
		LastHitCount,
		YoloBoxes.Num());

	return FFileHelper::SaveStringToFile(Row, *CsvPath, FFileHelper::EEncodingOptions::AutoDetect, &IFileManager::Get(), FILEWRITE_Append);
}

bool USonarScannerComponent::SaveMetaJson(const FString& AbsolutePath, const FString& SonarImagePath, const FString& LabelPath, const FString& RgbImagePath, const FString& PointCloudCsvPath, const FString& PointCloudPlyPath) const
{
	const AActor* Owner = GetOwner();
	TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
	Root->SetNumberField(TEXT("frame_index"), FrameIndex);
	Root->SetNumberField(TEXT("hit_count"), LastHitCount);
	Root->SetNumberField(TEXT("point_count"), WorldHitPoints.Num());
	Root->SetNumberField(TEXT("object_count"), YoloBoxes.Num());
	Root->SetBoolField(TEXT("only_label_tagged_actors"), bOnlyLabelTaggedActors);
	Root->SetNumberField(TEXT("trace_length_cm"), TraceLength);
	Root->SetNumberField(TEXT("num_traces"), NumTraces);
	Root->SetNumberField(TEXT("degrees_per_trace"), DegreesPerTrace);
	Root->SetNumberField(TEXT("vertical_samples"), VerticalSamples);
	Root->SetNumberField(TEXT("vertical_fov_degrees"), VerticalFovDegrees);
	Root->SetNumberField(TEXT("center_pitch_offset_degrees"), CenterPitchOffsetDegrees);
	Root->SetNumberField(TEXT("image_width"), ImageWidth);
	Root->SetNumberField(TEXT("image_height"), ImageHeight);
	Root->SetNumberField(TEXT("rgb_image_width"), IsValid(RgbRenderTarget) ? RgbRenderTarget->SizeX : RgbImageWidth);
	Root->SetNumberField(TEXT("rgb_image_height"), IsValid(RgbRenderTarget) ? RgbRenderTarget->SizeY : RgbImageHeight);
	Root->SetNumberField(TEXT("rgb_fov_degrees"), RgbFovDegrees);
	Root->SetNumberField(TEXT("rgb_exposure_bias"), RgbExposureBias);
	Root->SetBoolField(TEXT("rgb_exposure_locked"), bLockRgbExposure);
	Root->SetStringField(TEXT("sonar_image"), SonarImagePath);
	Root->SetStringField(TEXT("label_file"), LabelPath);
	Root->SetStringField(TEXT("rgb_image"), RgbImagePath);
	Root->SetStringField(TEXT("point_cloud_csv"), PointCloudCsvPath);
	Root->SetStringField(TEXT("point_cloud_ply"), PointCloudPlyPath);
	Root->SetStringField(TEXT("point_cloud_unit"), TEXT("m"));

	if (Owner)
	{
		const FVector Location = Owner->GetActorLocation();
		const FRotator Rotation = Owner->GetActorRotation();
		Root->SetStringField(TEXT("owner_name"), Owner->GetName());
		Root->SetArrayField(TEXT("owner_location_cm"), {
			MakeShared<FJsonValueNumber>(Location.X),
			MakeShared<FJsonValueNumber>(Location.Y),
			MakeShared<FJsonValueNumber>(Location.Z)
		});
		Root->SetArrayField(TEXT("owner_rotation_deg"), {
			MakeShared<FJsonValueNumber>(Rotation.Roll),
			MakeShared<FJsonValueNumber>(Rotation.Pitch),
			MakeShared<FJsonValueNumber>(Rotation.Yaw)
		});
	}

	TArray<TSharedPtr<FJsonValue>> ActorsJson;
	for (const FSonarYoloBox& Box : YoloBoxes)
	{
		TSharedRef<FJsonObject> ActorObject = MakeShared<FJsonObject>();
		ActorObject->SetStringField(TEXT("actor_name"), Box.ActorName);
		ActorObject->SetNumberField(TEXT("class_id"), Box.ClassId);
		ActorObject->SetArrayField(TEXT("center_normalized"), {
			MakeShared<FJsonValueNumber>(Box.CenterNormalized.X),
			MakeShared<FJsonValueNumber>(Box.CenterNormalized.Y)
		});
		ActorObject->SetArrayField(TEXT("size_normalized"), {
			MakeShared<FJsonValueNumber>(Box.SizeNormalized.X),
			MakeShared<FJsonValueNumber>(Box.SizeNormalized.Y)
		});
		ActorsJson.Add(MakeShared<FJsonValueObject>(ActorObject));
	}
	Root->SetArrayField(TEXT("objects"), ActorsJson);

	FString JsonText;
	const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&JsonText);
	if (!FJsonSerializer::Serialize(Root, Writer))
	{
		return false;
	}

	return FFileHelper::SaveStringToFile(JsonText, *AbsolutePath);
}

bool USonarScannerComponent::SaveCurrentFrame(bool bSaveRgb, FString& SonarImagePath, FString& LabelPath, FString& MetaPath, FString& RgbImagePath)
{
	if (bSaveRgb)
	{
		SetupAutoRgbCapture();
	}

	if (bScanBeforeSaving)
	{
		const bool bOriginalDrawDebug = bDrawDebug;
		if (bSaveRgb && bSuppressDebugForRgbCapture)
		{
			bDrawDebug = false;
		}
		Scan();
		bDrawDebug = bOriginalDrawDebug;
	}

	const FString RootDir = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir(), OutputDirectory);
	const FString SonarDir = RootDir / TEXT("images_sonar");
	const FString LabelDir = RootDir / TEXT("labels");
	const FString MetaDir = RootDir / TEXT("meta");
	const FString RgbDir = RootDir / TEXT("images_rgb");
	const FString PointsCsvDir = RootDir / TEXT("points_csv");
	const FString PointsPlyDir = RootDir / TEXT("points_ply");

	IFileManager::Get().MakeDirectory(*SonarDir, true);
	IFileManager::Get().MakeDirectory(*LabelDir, true);
	IFileManager::Get().MakeDirectory(*MetaDir, true);
	if (bSaveRgb)
	{
		IFileManager::Get().MakeDirectory(*RgbDir, true);
	}
	if (bSavePointCloudWithDatasetFrame && bSavePointCloudCsv)
	{
		IFileManager::Get().MakeDirectory(*PointsCsvDir, true);
	}
	if (bSavePointCloudWithDatasetFrame && bSavePointCloudPly)
	{
		IFileManager::Get().MakeDirectory(*PointsPlyDir, true);
	}

	while (IFileManager::Get().FileExists(*(SonarDir / (GetFrameStem() + TEXT("_sonar.png")))))
	{
		++FrameIndex;
	}

	const FString Stem = GetFrameStem();
	SonarImagePath = SonarDir / (Stem + TEXT("_sonar.png"));
	LabelPath = LabelDir / (Stem + TEXT(".txt"));
	MetaPath = MetaDir / (Stem + TEXT(".json"));
	RgbImagePath = bSaveRgb ? RgbDir / (Stem + TEXT("_rgb.png")) : FString();
	const FString PointCloudCsvPath = bSavePointCloudWithDatasetFrame && bSavePointCloudCsv ? PointsCsvDir / (Stem + TEXT("_points.csv")) : FString();
	const FString PointCloudPlyPath = bSavePointCloudWithDatasetFrame && bSavePointCloudPly ? PointsPlyDir / (Stem + TEXT("_points.ply")) : FString();
	const FString RelativeSonarImagePath = TEXT("images_sonar/") + Stem + TEXT("_sonar.png");
	const FString RelativeLabelPath = TEXT("labels/") + Stem + TEXT(".txt");
	const FString RelativeMetaPath = TEXT("meta/") + Stem + TEXT(".json");
	const FString RelativeRgbImagePath = bSaveRgb ? TEXT("images_rgb/") + Stem + TEXT("_rgb.png") : FString();
	const FString RelativePointCloudCsvPath = bSavePointCloudWithDatasetFrame && bSavePointCloudCsv ? TEXT("points_csv/") + Stem + TEXT("_points.csv") : FString();
	const FString RelativePointCloudPlyPath = bSavePointCloudWithDatasetFrame && bSavePointCloudPly ? TEXT("points_ply/") + Stem + TEXT("_points.ply") : FString();

	TArray<FColor> SonarPixels;
	GenerateSonarImage(SonarPixels);
	const bool bSavedSonar = SavePngFile(SonarImagePath, SonarPixels, FMath::RoundToInt(ImageWidth), FMath::RoundToInt(ImageHeight));
	const bool bSavedLabel = FFileHelper::SaveStringToFile(YoloText, *LabelPath);
	const bool bSavedRgb = !bSaveRgb || SaveRgbRenderTarget(RgbImagePath);
	const bool bSavedPointCloudCsv = !bSavePointCloudWithDatasetFrame || !bSavePointCloudCsv || SavePointCloudCsvFile(PointCloudCsvPath);
	const bool bSavedPointCloudPly = !bSavePointCloudWithDatasetFrame || !bSavePointCloudPly || SavePointCloudPlyFile(PointCloudPlyPath);
	const bool bSavedMeta = SaveMetaJson(MetaPath, RelativeSonarImagePath, RelativeLabelPath, RelativeRgbImagePath, RelativePointCloudCsvPath, RelativePointCloudPlyPath);
	const bool bSavedManifest = AppendManifestRow(RootDir, Stem, RelativeSonarImagePath, RelativeLabelPath, RelativeMetaPath, RelativeRgbImagePath, RelativePointCloudCsvPath, RelativePointCloudPlyPath);

	const bool bSuccess = bSavedSonar && bSavedLabel && bSavedRgb && bSavedPointCloudCsv && bSavedPointCloudPly && bSavedMeta && bSavedManifest;
	if (bSuccess)
	{
		++FrameIndex;
	}

	return bSuccess;
}

bool USonarScannerComponent::SaveDatasetFrame()
{
	FString SonarImagePath;
	FString LabelPath;
	FString MetaPath;
	FString RgbImagePath;
	return SaveCurrentFrame(bSaveRgbWithDatasetFrame, SonarImagePath, LabelPath, MetaPath, RgbImagePath);
}
