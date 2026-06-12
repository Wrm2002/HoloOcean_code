#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "SonarDatasetBlueprintLibrary.generated.h"

USTRUCT(BlueprintType)
struct FSonarYoloBox
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Sonar Dataset")
	TObjectPtr<AActor> Actor = nullptr;

	UPROPERTY(BlueprintReadOnly, Category = "Sonar Dataset")
	FString ActorName;

	UPROPERTY(BlueprintReadOnly, Category = "Sonar Dataset")
	int32 ClassId = 0;

	UPROPERTY(BlueprintReadOnly, Category = "Sonar Dataset")
	FVector2D MinPixel = FVector2D::ZeroVector;

	UPROPERTY(BlueprintReadOnly, Category = "Sonar Dataset")
	FVector2D MaxPixel = FVector2D::ZeroVector;

	UPROPERTY(BlueprintReadOnly, Category = "Sonar Dataset")
	FVector2D CenterPixel = FVector2D::ZeroVector;

	UPROPERTY(BlueprintReadOnly, Category = "Sonar Dataset")
	FVector2D SizePixel = FVector2D::ZeroVector;

	UPROPERTY(BlueprintReadOnly, Category = "Sonar Dataset")
	FVector2D CenterNormalized = FVector2D::ZeroVector;

	UPROPERTY(BlueprintReadOnly, Category = "Sonar Dataset")
	FVector2D SizeNormalized = FVector2D::ZeroVector;

	UPROPERTY(BlueprintReadOnly, Category = "Sonar Dataset")
	FString YoloLine;
};

UCLASS()
class SONARDATASETTOOLS_API USonarDatasetBlueprintLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	UFUNCTION(BlueprintPure, Category = "Sonar Dataset")
	static FVector2D LocalPointToSonarPixel(
		FVector LocalPoint,
		float TraceLength,
		float OriginX = 256.0f,
		float OriginY = 512.0f,
		float DrawRadius = 500.0f,
		bool bClampToImage = true,
		float ImageWidth = 512.0f,
		float ImageHeight = 512.0f);

	UFUNCTION(BlueprintPure, Category = "Sonar Dataset")
	static bool WorldPointToSonarPixel(
		AActor* ReferenceActor,
		FVector WorldPoint,
		float TraceLength,
		FVector& LocalPoint,
		FVector2D& PixelPoint,
		float OriginX = 256.0f,
		float OriginY = 512.0f,
		float DrawRadius = 500.0f,
		bool bClampToImage = true,
		float ImageWidth = 512.0f,
		float ImageHeight = 512.0f);

	UFUNCTION(BlueprintCallable, Category = "Sonar Dataset")
	static void BuildSonarPointsFromHits(
		AActor* ReferenceActor,
		const TArray<FVector>& WorldHitPoints,
		float TraceLength,
		TArray<FVector>& LocalPoints,
		TArray<FVector2D>& PixelPoints,
		float OriginX = 256.0f,
		float OriginY = 512.0f,
		float DrawRadius = 500.0f,
		bool bClampToImage = true,
		float ImageWidth = 512.0f,
		float ImageHeight = 512.0f);

	UFUNCTION(BlueprintCallable, Category = "Sonar Dataset")
	static void BuildYoloBoxesFromSonarPixels(
		const TArray<FVector2D>& PixelPoints,
		const TArray<AActor*>& HitActors,
		float ImageWidth,
		float ImageHeight,
		int32 DefaultClassId,
		TArray<FSonarYoloBox>& Boxes,
		FString& YoloText);
};
