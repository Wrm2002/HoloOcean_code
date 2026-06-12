#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "SonarDatasetBlueprintLibrary.h"
#include "SonarScannerComponent.generated.h"

class UTextureRenderTarget2D;
class USceneCaptureComponent2D;

UCLASS(ClassGroup=(Sonar), meta=(BlueprintSpawnableComponent))
class SONARDATASETTOOLS_API USonarScannerComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	USonarScannerComponent();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Scan")
	bool bScanEveryTick = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Scan", meta = (ClampMin = "1"))
	int32 NumTraces = 600;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Scan")
	float DegreesPerTrace = 0.2f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Scan", meta = (ClampMin = "1.0"))
	float TraceLength = 5000.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Scan")
	float CenterYawOffsetDegrees = 0.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Scan", meta = (ClampMin = "1"))
	int32 VerticalSamples = 5;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Scan", meta = (ClampMin = "0.0"))
	float VerticalFovDegrees = 20.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Scan")
	float CenterPitchOffsetDegrees = 0.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Scan")
	FVector LocalOriginOffset = FVector(120.0f, 0.0f, 60.0f);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Scan")
	TEnumAsByte<ECollisionChannel> TraceChannel = ECC_Visibility;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Debug")
	bool bDrawDebug = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Debug")
	float DebugLineDuration = 0.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Debug")
	bool bDrawAllVerticalDebugRays = false;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Image")
	float SonarOriginX = 256.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Image")
	float SonarOriginY = 512.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Image")
	float SonarDrawRadius = 500.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Image")
	float ImageWidth = 512.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Image")
	float ImageHeight = 512.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Image")
	bool bClampPixelsToImage = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Labels")
	bool bBuildYoloEveryScan = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Labels")
	int32 DefaultClassId = 0;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Labels")
	bool bOnlyLabelTaggedActors = true;

	UPROPERTY(BlueprintReadOnly, Category = "Sonar|Output")
	TArray<FVector> WorldHitPoints;

	UPROPERTY(BlueprintReadOnly, Category = "Sonar|Output")
	TArray<FVector> LocalHitPoints;

	UPROPERTY(BlueprintReadOnly, Category = "Sonar|Output")
	TArray<FVector2D> SonarPixelPoints;

	UPROPERTY(BlueprintReadOnly, Category = "Sonar|Output")
	TArray<TObjectPtr<AActor>> HitActors;

	UPROPERTY(BlueprintReadOnly, Category = "Sonar|Output")
	TArray<float> HitDistances;

	UPROPERTY(BlueprintReadOnly, Category = "Sonar|Output")
	TArray<FVector> HitNormals;

	UPROPERTY(BlueprintReadOnly, Category = "Sonar|Output")
	TArray<float> HitIntensities;

	UPROPERTY(BlueprintReadOnly, Category = "Sonar|Output")
	TArray<FSonarYoloBox> YoloBoxes;

	UPROPERTY(BlueprintReadOnly, Category = "Sonar|Output")
	FString YoloText;

	UPROPERTY(BlueprintReadOnly, Category = "Sonar|Output")
	int32 LastHitCount = 0;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Image Render", meta = (ClampMin = "1"))
	int32 PingRadiusPixels = 2;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Image Render")
	bool bUseRealisticEcho = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Image Render", meta = (ClampMin = "0.1"))
	float EchoAngularSigmaPixels = 2.5f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Image Render", meta = (ClampMin = "0.1"))
	float EchoRangeSigmaPixels = 6.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Image Render", meta = (ClampMin = "0.0", ClampMax = "1.0"))
	float EchoTailStrength = 0.35f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Image Render")
	bool bDrawAcousticShadow = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Image Render", meta = (ClampMin = "1"))
	int32 ShadowLengthPixels = 180;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Image Render", meta = (ClampMin = "0.0", ClampMax = "1.0"))
	float ShadowStrength = 0.72f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Image Render")
	bool bDrawFanBackground = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Image Render", meta = (ClampMin = "0", ClampMax = "255"))
	int32 FanBackgroundValue = 8;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Image Render")
	bool bDrawRangeRings = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Image Render", meta = (ClampMin = "1"))
	int32 RangeRingSpacingPixels = 64;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Image Render", meta = (ClampMin = "0", ClampMax = "255"))
	int32 RangeRingValue = 22;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Image Render", meta = (ClampMin = "0.0"))
	float IntensityScale = 255.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Image Render")
	bool bApplyDistanceFalloff = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Acoustic Material")
	bool bApplyMaterialReflectivity = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Acoustic Material", meta = (ClampMin = "0.0"))
	float RockReflectivity = 1.15f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Acoustic Material", meta = (ClampMin = "0.0"))
	float MetalReflectivity = 1.55f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Acoustic Material", meta = (ClampMin = "0.0"))
	float SandReflectivity = 0.62f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Acoustic Material", meta = (ClampMin = "0.0"))
	float PlantReflectivity = 0.42f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Noise")
	bool bUseGaussianNoise = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Noise", meta = (ClampMin = "0.0"))
	float BackgroundNoiseStdDev = 3.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Noise", meta = (ClampMin = "0.0"))
	float PingNoiseStdDev = 10.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Output Files")
	FString OutputDirectory = TEXT("Saved/SonarDataset");

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Output Files")
	FString FilePrefix = TEXT("");

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Output Files")
	int32 FrameIndex = 0;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Output Files")
	bool bScanBeforeSaving = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Output Files")
	bool bAutoSaveDatasetFrames = false;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Output Files", meta = (ClampMin = "0.01"))
	float AutoSaveIntervalSeconds = 1.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Output Files", meta = (ClampMin = "0"))
	int32 MaxAutoSaveFrames = 0;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|RGB")
	bool bSaveRgbWithDatasetFrame = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|RGB")
	bool bSuppressDebugForRgbCapture = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|RGB")
	bool bAutoCreateRgbCapture = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|RGB", meta = (ClampMin = "16"))
	int32 RgbImageWidth = 1280;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|RGB", meta = (ClampMin = "16"))
	int32 RgbImageHeight = 720;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|RGB")
	float RgbFovDegrees = 90.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|RGB")
	FVector RgbLocalOffset = FVector(120.0f, 0.0f, 80.0f);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|RGB")
	bool bLockRgbExposure = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|RGB", meta = (ClampMin = "-10.0", ClampMax = "10.0"))
	float RgbExposureBias = 2.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|RGB")
	TObjectPtr<UTextureRenderTarget2D> RgbRenderTarget = nullptr;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Sonar|RGB")
	TObjectPtr<USceneCaptureComponent2D> AutoRgbCapture = nullptr;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Point Cloud")
	bool bSavePointCloudWithDatasetFrame = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Point Cloud")
	bool bSavePointCloudCsv = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Point Cloud")
	bool bSavePointCloudPly = true;

	UFUNCTION(BlueprintCallable, Category = "Sonar")
	void Scan();

	UFUNCTION(BlueprintCallable, Category = "Sonar")
	void ClearScanData();

	UFUNCTION(BlueprintCallable, Category = "Sonar|Output Files")
	bool SaveCurrentFrame(bool bSaveRgb, FString& SonarImagePath, FString& LabelPath, FString& MetaPath, FString& RgbImagePath);

	UFUNCTION(BlueprintCallable, Category = "Sonar|Output Files")
	bool SaveDatasetFrame();

	UFUNCTION(BlueprintCallable, Category = "Sonar|Image Render")
	void GenerateSonarImage(TArray<FColor>& Pixels) const;

	UFUNCTION(BlueprintPure, Category = "Sonar|Output Files")
	FString GetFrameStem() const;

protected:
	virtual void BeginPlay() override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

private:
	void SetupAutoRgbCapture();
	float GenerateGaussian(float StdDev) const;
	bool SavePngFile(const FString& AbsolutePath, const TArray<FColor>& Pixels, int32 Width, int32 Height) const;
	bool SaveRgbRenderTarget(const FString& AbsolutePath) const;
	bool SavePointCloudCsvFile(const FString& AbsolutePath) const;
	bool SavePointCloudPlyFile(const FString& AbsolutePath) const;
	bool SaveMetaJson(const FString& AbsolutePath, const FString& SonarImagePath, const FString& LabelPath, const FString& RgbImagePath, const FString& PointCloudCsvPath, const FString& PointCloudPlyPath) const;
	bool AppendManifestRow(const FString& RootDir, const FString& Stem, const FString& SonarImagePath, const FString& LabelPath, const FString& MetaPath, const FString& RgbImagePath, const FString& PointCloudCsvPath, const FString& PointCloudPlyPath) const;

	float AutoSaveAccumulatorSeconds = 0.0f;
	int32 AutoSavedFrameCount = 0;
};
